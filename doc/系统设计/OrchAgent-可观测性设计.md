# OrchAgent — 可观测性设计

---

## 一、可观测性三支柱

```
┌──────────────────────────────────────────────────────────┐
│                        可观测性                            │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   日志 Logs   │  │  指标 Metrics│  │ 追踪 Traces   │   │
│  │ structlog    │  │ Prometheus   │  │ OpenTelemetry│   │
│  │              │  │ + Grafana    │  │ + Jaeger     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│  做什么？         多不多？         哪里慢？              │
└──────────────────────────────────────────────────────────┘
```

---

## 二、结构化日志

### 配置

```python
import structlog
import logging

def setup_logging(env: str = "prod"):
    if env == "dev":
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            logger_factory=structlog.PrintLoggerFactory(),
        )
    else:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            logger_factory=structlog.WriteLoggerFactory(
                file=Path("logs/app.log").open("a")
            ),
        )

logger = structlog.get_logger()
```

### 日志规范

```python
# 好的日志（结构化，有上下文）
logger.info(
    "llm_call_completed",
    request_id="req_abc123",
    execution_id="exec_xyz",
    agent_id="agent_001",
    provider="openai",
    model="gpt-4o",
    token_usage={"prompt": 2345, "completion": 512, "total": 2857},
    latency_ms=1450,
    success=True,
)

logger.info(
    "tool_executed",
    execution_id="exec_xyz",
    node_id="node_3",
    tool_name="nl2sql_execute_query",
    latency_ms=320,
    row_count=42,
    success=True,
)

logger.info(
    "workflow_step_completed",
    execution_id="exec_xyz",
    workflow_id="wf_001",
    node_id="node_5",
    node_type="agent",
    step_number=3,
    total_steps=8,
    duration_ms=2340,
)
```

### 请求上下文绑定

```python
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host,
        )

        start = time.time()
        response = await call_next(request)
        elapsed = (time.time() - start) * 1000

        logger.info(
            "request_completed",
            status_code=response.status_code,
            latency_ms=round(elapsed),
        )

        structlog.contextvars.clear_contextvars()
        return response
```

### 日志级别规范

| 级别 | 使用场景 |
|------|---------|
| DEBUG | LLM prompt 内容、中间结果 |
| INFO | 正常流程事件（调用完成、任务提交、状态变更） |
| WARNING | 可恢复的异常（重试、降级、熔断、限流） |
| ERROR | LLM 超时、工具失败、DB 异常 |
| CRITICAL | 系统级故障（无法恢复） |

---

## 三、指标采集 (Prometheus)

```python
from prometheus_client import Counter, Histogram, Gauge

# LLM 调用指标
llm_call_total = Counter(
    "agent_llm_call_total",
    "Total LLM call count",
    ["provider", "model", "status"],
)

llm_call_duration = Histogram(
    "agent_llm_call_duration_seconds",
    "LLM call duration",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)

llm_token_usage = Counter(
    "agent_llm_token_usage_total",
    "Total tokens consumed",
    ["provider", "model", "type"],
)

# 工具调用指标
tool_call_total = Counter(
    "agent_tool_call_total",
    "Total tool call count",
    ["tool_name", "tool_type", "status"],
)

tool_call_duration = Histogram(
    "agent_tool_call_duration_seconds",
    "Tool call duration",
    ["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 5, 10],
)

# 工作流指标
workflow_execution_total = Counter(
    "agent_workflow_execution_total",
    "Total workflow execution count",
    ["workflow_id", "status"],
)

workflow_execution_duration = Histogram(
    "agent_workflow_execution_duration_seconds",
    "Workflow execution duration",
    ["workflow_id"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

# 系统指标
active_executions = Gauge(
    "agent_active_executions",
    "Currently running executions",
)

queue_depth = Gauge(
    "agent_queue_depth",
    "Task queue depth",
    ["queue_name"],
)

# API 指标
api_request_total = Counter(
    "agent_api_request_total",
    "API request count",
    ["method", "endpoint", "status_code"],
)

api_request_duration = Histogram(
    "agent_api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"],
)
```

### 指标端点

```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
```

### 指标记录装饰器

```python
class MetricsMixin:
    @contextmanager
    def track_llm_call(self, provider: str, model: str):
        start = time.time()
        try:
            yield
            llm_call_total.labels(provider, model, "success").inc()
        except Exception:
            llm_call_total.labels(provider, model, "failed").inc()
            raise
        finally:
            duration = time.time() - start
            llm_call_duration.labels(provider, model).observe(duration)
```

---

## 四、链路追踪 (OpenTelemetry + Jaeger)

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def setup_tracing(app: FastAPI):
    provider = TracerProvider(
        resource=Resource.create({
            "service.name": "orchagent",
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENV", "dev"),
        })
    )

    exporter = OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    RedisInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()

tracer = trace.get_tracer("orchagent")
```

---

## 五、健康检查端点

```python
@router.get("/health/live")
async def liveness():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends()):
    checks = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}

@router.get("/health/detailed")
async def detailed_health():
    return {
        "status": "ok",
        "uptime_seconds": time.time() - START_TIME,
        "components": {
            "database": await check_postgres(),
            "redis": await check_redis(),
            "llm_providers": {
                "openai": await check_llm("openai"),
                "deepseek": await check_llm("deepseek"),
            },
            "mcp_servers": await check_mcp_servers(),
        },
        "circuit_breakers": await get_cb_states(),
        "active_executions": await get_active_count(),
        "error_rate_5min": await get_error_rate(300),
    }
```

---

## 六、Grafana 仪表盘建议

### 核心面板

```
Grafana Dashboard: OrchAgent

Row 1: 概览
  [活跃执行数] [LLM QPS] [错误率(5min)]

Row 2: LLM 性能
  [LLM 调用延迟 P50/P95/P99 时间序列折线图，按 Provider 分组]

Row 3: Token 用量
  [Token 消耗趋势(面积图)] [Token 按模型分布(饼图)]

Row 4: 工作流
  [工作流成功率(折线图)] [平均执行时长(柱状图)]

Row 5: 工具
  [工具调用量 Top 10(柱状图)] [工具错误率(表格)]
```

### PromQL 查询示例

```promql
# LLM 调用 QPS
rate(agent_llm_call_total[1m])

# LLM 调用 P95 延迟
histogram_quantile(0.95, 
  rate(agent_llm_call_duration_seconds_bucket[5m]))

# Token 消耗速率 (每秒)
rate(agent_llm_token_usage_total[5m])

# 工作流成功率
sum(rate(agent_workflow_execution_total{status="completed"}[5m]))
  /
sum(rate(agent_workflow_execution_total[5m]))

# 活跃执行数
agent_active_executions
```

---

## 七、告警规则

```yaml
groups:
  - name: orchagent_alerts
    rules:
      - alert: HighLLMErrorRate
        expr: |
          rate(agent_llm_call_total{status="failed"}[5m])
          / rate(agent_llm_call_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM 调用错误率超过 5%"

      - alert: HighLLMLatency
        expr: |
          histogram_quantile(0.95,
            rate(agent_llm_call_duration_seconds_bucket[5m])) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM 调用 P95 延迟超过 10 秒"

      - alert: LowWorkflowSuccessRate
        expr: |
          sum(rate(agent_workflow_execution_total{status="completed"}[30m]))
          / sum(rate(agent_workflow_execution_total[30m])) < 0.80
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "工作流成功率低于 80%"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
```

---

## 八、Docker Compose 集成

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "4317:4317"
    environment:
      COLLECTOR_OTLP_ENABLED: "true"

volumes:
  prometheus_data:
  grafana_data:
```

---

## 九、目录总结

| 组件 | 技术 | 用途 | 端口 |
|------|------|------|------|
| structlog | Python | 结构化日志，输出 JSON | - |
| Prometheus | 时序数据库 | 指标采集 | 9090 |
| Grafana | 可视化 | 仪表盘 + 告警 | 3000 |
| Jaeger | 链路追踪 | 全链路耗时分析 | 16686 |
| OpenTelemetry | 追踪 SDK | 自动/手动 Span | - |

开发阶段可以只装 structlog，Prometheus/Grafana/Jaeger 到部署阶段再加。
