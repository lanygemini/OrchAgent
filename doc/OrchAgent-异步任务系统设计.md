# OrchAgent — 异步任务系统设计

---

## 一、为什么需要异步任务系统

FastAPI + asyncio 适合 I/O 密集请求，但以下场景不宜在请求线程中执行：

| 场景 | 阻塞时间 | 需要异步任务 |
|------|---------|------------|
| L3 记忆提取 | 5~30s | 会话结束后异步 |
| 记忆清理（定时衰减） | 定时触发 | 定时任务 |
| Token 用量批量同步 | 定时触发 | 定时任务 |
| 长时间工作流执行 (>5min) | 5~30min | 免超时 |
| 批量文档导入知识库 | 10~60min | 大文件处理 |
| 执行完成通知 | 1~3s | 不阻塞返回 |

---

## 二、技术选型

**推荐 ARQ**（基于 Redis，API 和 asyncio 一致，简单够用）

| 方案 | 依赖 | 优点 | 缺点 |
|------|------|------|------|
| ARQ | Redis | 极简，API 像 asyncio | 功能少于 Celery |
| Celery | Redis/RabbitMQ | 功能最全 | 配置复杂 |

---

## 三、ARQ 配置与启动

### Worker 配置

```python
# arq_worker.py
from arq.connections import RedisSettings

class WorkerSettings:
    redis_settings = RedisSettings(host="localhost", port=6379, database=1)
    functions = []  # 注册在 worker 启动文件中
    max_jobs: int = 20
    job_timeout: int = 3600
    keep_result: int = 3600
    health_check_interval: int = 30
```

### Scheduler 配置

```python
# arq_scheduler.py
from arq import cron

class SchedulerSettings:
    redis_settings = RedisSettings(host="localhost", port=6379, database=2)
    cron_jobs = [
        cron(cleanup_memories)(hour=3, minute=0),
        cron(sync_token_usage)(
            minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}
        ),
    ]
    job_timeout = 3600
```

### FastAPI 集成

```python
# app/tasks/worker.py
from arq import create_pool
from arq.connections import ArqRedis

redis_pool: ArqRedis = None

async def init_arq(redis_url: str):
    global redis_pool
    redis_pool = await create_pool(RedisSettings.from_dsn(redis_url))

async def get_arq() -> ArqRedis:
    return redis_pool

# app/main.py
@app.on_event("startup")
async def startup():
    await init_arq(app.state.redis_url)
```

---

## 四、任务函数实现

### 记忆提取任务

```python
# app/tasks/memory_tasks.py
async def extract_memories(
    ctx, agent_id: str, session_id: str, messages_data: list
):
    """单个会话的记忆提取"""
    db = ctx.get("db")
    messages = [deserialize_message(m) for m in messages_data]
    memory_store = EpisodicMemoryStore(db, ctx["embedding_model"])
    await memory_store.extract_and_store(agent_id, session_id, messages)
    return {"success": True, "agent_id": agent_id}
```

### 长时间工作流任务

```python
# app/tasks/workflow_tasks.py
async def execute_long_workflow(
    ctx, workflow_id: str, execution_id: str,
    input_data: dict, user_id: str,
):
    """执行长时间运行的工作流（免 FastAPI 请求超时）"""
    db = ctx["db"]

    execution = await db.get(Execution, execution_id)
    execution.status = "running"
    await db.commit()

    compiler = WorkflowCompiler(db)
    dag = await _load_dag(db, workflow_id)
    graph = compiler.compile(dag)

    config = {"configurable": {"thread_id": f"exec:{execution_id}"}}
    streamer = ExecutionStreamer(ctx["redis"])

    initial_state = {
        "workflow_id": workflow_id,
        "execution_id": execution_id,
        "context": input_data,
        "messages": [HumanMessage(content=input_data.get("input_text", ""))],
    }

    try:
        async for event in graph.astream_events(initial_state, config):
            await streamer.publish(execution_id, event)

        execution.status = "completed"
        execution.completed_at = datetime.utcnow()
        await db.commit()

        return {"success": True, "execution_id": execution_id}
    except Exception as e:
        execution.status = "failed"
        execution.error_message = str(e)
        await db.commit()
        raise


async def cancel_workflow(ctx, execution_id: str):
    """取消正在执行的工作流"""
    db = ctx["db"]
    execution = await db.get(Execution, execution_id)
    if execution.status == "running":
        execution.status = "cancelled"
        execution.completed_at = datetime.utcnow()
        await db.commit()
    return {"success": True}
```

### 通知任务

```python
# app/tasks/notification_tasks.py
async def send_execution_complete(ctx, execution_id: str, user_id: str):
    """发送执行完成通知"""
    db = ctx["db"]
    notification = Notification(
        user_id=user_id,
        type="execution_complete",
        title="工作流执行完成",
        content=f"执行 ID: {execution_id}",
        data={"execution_id": execution_id},
    )
    db.add(notification)
    await db.commit()


async def send_budget_warning(ctx, user_id: str, period: str, used: int, limit: int):
    """发送预算告警通知"""
    notification = Notification(
        user_id=user_id,
        type="budget_warning",
        title=f"{period}预算告警",
        content=f"Token 用量已达 {period} 预算的 {(used/limit)*100:.0f}%",
    )
    db.add(notification)
    await db.commit()
```

### 维护任务

```python
# app/tasks/maintenance_tasks.py
async def cleanup_memories(ctx):
    """定期清理过期的长期记忆"""
    db = ctx["db"]

    await db.execute("""
        UPDATE episodic_memories
        SET importance = importance * 0.95
        WHERE last_accessed_at < NOW() - INTERVAL '30 days'
        AND importance > 0.05
    """)

    await db.execute("""
        DELETE FROM episodic_memories
        WHERE importance < 0.1
        AND last_accessed_at < NOW() - INTERVAL '90 days'
    """)

    deleted = db.get_result_proxy().rowcount
    await db.commit()
    return {"success": True, "deleted": deleted}


async def sync_token_usage(ctx):
    """每5分钟批量同步 Redis -> PostgreSQL Token 用量"""
    db = ctx["db"]
    redis = ctx["redis"]

    active_keys = await redis.keys("token_usage:*:day")
    user_ids = set(k.decode().split(":")[1] for k in active_keys)

    synced = 0
    for user_id in user_ids:
        daily = int(await redis.get(f"token_usage:{user_id}:day") or 0)
        daily_cost = float(await redis.get(f"cost_usage:{user_id}:day") or 0)

        today = datetime.utcnow().date()
        usage = await db.execute(
            select(DailyUsage).where(
                DailyUsage.user_id == user_id,
                DailyUsage.date == today,
            )
        )
        usage = usage.scalar_one_or_none()

        if usage:
            usage.total_tokens = daily
            usage.total_cost = daily_cost
        else:
            db.add(DailyUsage(
                user_id=user_id, date=today,
                total_tokens=daily, total_cost=daily_cost,
            ))
        synced += 1

    await db.commit()
    return {"success": True, "synced_users": synced}
```

---

## 五、任务提交（FastAPI）

```python
@router.post("/api/v1/tasks/memory/extract")
async def trigger_memory_extraction(request, arq: ArqRedis = Depends(get_arq)):
    job = await arq.enqueue_job(
        "extract_memories",
        agent_id=request.agent_id,
        session_id=request.session_id,
        messages_data=request.messages,
        _job_id=f"mem:{request.session_id}",
    )
    return {"task_id": job.job_id, "status": "queued"}


@router.get("/api/v1/tasks/{task_id}/status")
async def get_task_status(task_id: str, arq: ArqRedis = Depends(get_arq)):
    job = await arq.get_job_result(task_id)
    if job is None:
        return {"status": "queued"}
    if job.success:
        return {"status": "completed", "result": job.result}
    return {"status": "failed", "error": str(job.result)}
```

---

## 六、Docker 部署

```yaml
services:
  arq_worker:
    build: ./backend
    command: arq arq_worker.WorkerSettings
    env_file: .env
    depends_on: [redis, postgres]
    restart: always
    deploy:
      replicas: 2

  arq_scheduler:
    build: ./backend
    command: arq arq_scheduler.SchedulerSettings
    env_file: .env
    depends_on: [redis, postgres]
    restart: always
```

---

## 七、队列隔离

```python
class TaskQueue(str, Enum):
    DEFAULT = "arq:queue"
    MEMORY = "arq:memory_queue"
    NOTIFICATION = "arq:notify_queue"
    WORKFLOW = "arq:workflow_queue"
```

---

## 八、任务清单汇总

| 任务名 | 触发方式 | 频率 |
|--------|---------|------|
| 记忆提取 | 会话结束时 enqueue | 按需 |
| 长时间工作流 | 工作流提交时 | 按需 |
| 取消工作流 | 用户取消时 | 按需 |
| 执行完成通知 | 工作流完成后 | 按需 |
| 预算告警 | 预算超阈时 | 按需 |
| 记忆清理 | Cron (每天 3:00) | 定时 |
| Token用量同步 | Cron (每5分钟) | 定时 |
| 过期数据清理 | Cron (每周日 2:00) | 定时 |
