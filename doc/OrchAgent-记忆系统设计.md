# OrchAgent — 记忆系统架构设计

---

## 一、为什么记忆系统重要

```
没有记忆的 Agent              有完整记忆的 Agent
"您好！请问有什么可以帮您？"   "您好！上次我们聊到项目部署方案，
                             您说用的是阿里云ECS，我已经
                             帮你查了上次那个Docker配置..."
    ↑                              ↑
 每次都是全新对话            跨会话、跨时间、跨Agent的知识复用
```

---

## 二、四层记忆架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                       记忆系统分层                            │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  L4 — 知识记忆 (Knowledge Memory)                     │  │
│  │  跨 Agent、跨用户、跨会话的持久化知识                    │  │
│  │  用户画像 / 领域知识 / 工作流模板 / 工具使用经验         │  │
│  │  技术: pgvector + RAG 检索                             │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  L3 — 情节记忆 (Episodic Memory)                      │  │
│  │  同一 Agent 的历史会话摘要，跨会话追溯                   │  │
│  │  "上次用户问了XX，我建议了YY，结果..."                   │  │
│  │  技术: pgvector + 语义检索 + 时间衰减                   │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  L2 — 会话记忆 (Conversation Memory)                   │  │
│  │  单次会话内的对话历史，短窗口高保真                      │  │
│  │  最近N轮对话 / Token预算管理 / 自动摘要                 │  │
│  │  技术: Redis List + LangGraph State                   │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  L1 — 工作记忆 (Working Memory)                        │  │
│  │  单次工作流执行期间的运行时状态                          │  │
│  │  当前节点 / 工具结果 / 中间变量 / 路径追踪              │  │
│  │  技术: LangGraph AgentState + Checkpointer              │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 三、L1 — 工作记忆 (Working Memory)

工作流执行期间的运行时状态，由 LangGraph AgentState 承载，通过 Checkpointer 持久化。

### 状态定义

```python
from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    workflow_id: str
    execution_id: str
    context: Dict[str, Any]
    current_node: str
    next_nodes: List[str]
    path: List[str]
    tool_results: Dict[str, Any]
    needs_human_input: bool
    human_input: Optional[str]
    retrieved_memories: List[MemoryItem]
    collected_memories: List[MemoryItem]
    error: Optional[str]
```

### LangGraph Checkpointer 集成

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
graph = workflow.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "session-uuid"}}
result = await graph.ainvoke(initial_state, config)
```

### Checkpoint 配置项

```python
class CheckpointConfig:
    db_url: str
    save_interval: int = 1
    max_checkpoints: int = 100
    ttl_hours: int = 72
    compress_snapshots: bool = True
```

---

## 四、L2 — 会话记忆 (Conversation Memory)

单次会话内的对话历史管理，核心问题：**上下文窗口有限，如何高效利用？**

### 设计方案：三合一策略

```
                    ┌────────────────────┐
                    │   L2 会话记忆       │
                    ├────────────────────┤
                    │                    │
                    │  ① 滑动窗口        │
                    │  保留最近 N 轮      │
                    │  N=10~20 可配置    │
                    │                    │
                    │  ② Token 预算      │
                    │  总预算控制         │
                    │  默认 maxTokens    │
                    │  = 模型上限-2K     │
                    │                    │
                    │  ③ 自动摘要        │
                    │  超预算时触发       │
                    │  LLM 压缩旧消息    │
                    └────────────────────┘
```

### 实现代码

```python
class ConversationMemory:
    def __init__(
        self,
        redis: Redis,
        window_size: int = 20,
        max_tokens: int = 6000,
        summary_threshold: int = 15,
    ):
        self.redis = redis
        self.window_size = window_size
        self.max_tokens = max_tokens
        self.summary_threshold = summary_threshold

    async def add_message(self, session_id: str, message: BaseMessage):
        key = f"conv:{session_id}"
        data = message.model_dump_json()
        await self.redis.rpush(key, data)
        await self.redis.expire(key, 3600 * 24)

        length = await self.redis.llen(key)
        if length > self.summary_threshold:
            await self._maybe_summarize(session_id, key)

    async def get_context(self, session_id: str) -> List[BaseMessage]:
        key = f"conv:{session_id}"
        summary = await self.redis.get(f"conv:{session_id}:summary")
        summary_msg = summary and [SystemMessage(content=f"[历史对话摘要]\n{summary}")]
        raw = await self.redis.lrange(key, -self.window_size, -1)
        window_msgs = [self._deserialize(m) for m in raw]
        all_msgs = (summary_msg or []) + window_msgs
        return self._trim_by_token_budget(all_msgs)

    async def _maybe_summarize(self, session_id: str, key: str):
        old_messages = await self.redis.lrange(key, 0, -self.window_size - 1)
        summary = await self._generate_summary(old_messages)
        await self.redis.set(f"conv:{session_id}:summary", summary)
        await self.redis.ltrim(key, -self.window_size, -1)

    async def _generate_summary(self, messages: List[str]) -> str:
        summary_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        text = "\n".join(messages)
        prompt = f"请用中文简洁总结以下对话要点（不超过200字）：\n{text}"
        return (await summary_llm.ainvoke(prompt)).content

    def _trim_by_token_budget(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        total = 0
        result = []
        for msg in reversed(messages):
            tokens = estimate_tokens(msg.content)
            if total + tokens > self.max_tokens:
                break
            result.insert(0, msg)
            total += tokens
        return result
```

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `window_size` | 20 | 保留最近 N 轮对话原文 |
| `max_tokens` | 6000 | 总 Token 预算 |
| `summary_threshold` | 15 | 超过该消息数自动触发摘要 |
| `ttl` | 24h | Redis 中会话历史的过期时间 |

---

## 五、L3 — 情节记忆 (Episodic Memory)

跨会话长期记忆，核心生命周期：提取 -> 存储 -> 检索 -> 衰减。

### 数据模型

```python
class EpisodicMemory(Base):
    __tablename__ = "episodic_memories"

    id: str
    agent_id: str
    session_id: str
    content: str
    raw_messages: JSON
    embedding: Vector(1536)
    memory_type: str
    importance: float
    access_count: int
    created_at: datetime
    last_accessed_at: datetime
    ttl_days: Optional[int]
    is_active: bool
```

### 记忆类型枚举

```python
class MemoryType(str, Enum):
    USER_FACT = "user_fact"
    PREFERENCE = "preference"
    DECISION = "decision"
    TOOL_RESULT = "tool_result"
```

### 检索算法

```python
class EpisodicMemoryStore:
    def __init__(self, db: AsyncSession, embedding_model):
        self.db = db
        self.embedding = embedding_model

    async def retrieve(
        self, agent_id: str, query: str,
        top_k: int = 5, min_similarity: float = 0.6,
    ) -> List[MemoryItem]:
        query_embedding = await self.embedding.aembed_query(query)

        stmt = select(EpisodicMemory).where(
            EpisodicMemory.agent_id == agent_id,
            EpisodicMemory.is_active == True,
        ).order_by(
            (EpisodicMemory.embedding.cosine_distance(query_embedding) * -1
             + func.least(EpisodicMemory.importance, 1.0)
             * func.exp(-0.01 * func.extract('day',
                 func.now() - EpisodicMemory.last_accessed_at)
             ))
        ).limit(top_k)

        result = await self.db.execute(stmt)
        memories = result.scalars().all()

        return [
            m for m in memories
            if self._cosine_sim(query_embedding, m.embedding) >= min_similarity
        ]

    async def extract_and_store(
        self, agent_id: str, session_id: str, messages: List[BaseMessage],
    ):
        memories = await self._extract_memories(messages)
        existing = await self.retrieve(agent_id, " ".join([m.content for m in memories]))
        new_memories = [m for m in memories if not self._is_duplicate(m, existing)]

        for memory in new_memories:
            embedding = await self.embedding.aembed_query(memory.content)
            db_memory = EpisodicMemory(
                agent_id=agent_id, session_id=session_id,
                content=memory.content, embedding=embedding,
                memory_type=memory.type, importance=memory.importance,
            )
            self.db.add(db_memory)
        await self.db.commit()
```

### 检索评分算法

```
综合得分 = 余弦相似度 x 0.6 + 重要性得分 x 0.3 + 时间衰减 x 0.1

其中：
- 余弦相似度：embedding.cosine_distance(query)
- 重要性得分：importance x exp(-0.01 x 距上次访问天数)
- 时间衰减系数：exp(-0.01 x days_since_last_access)
```

### 定期清理

```python
@celery_app.task
async def cleanup_memories():
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

    await db.execute("""
        DELETE FROM episodic_memories
        WHERE ttl_days IS NOT NULL
        AND created_at + (ttl_days || ' days')::INTERVAL < NOW()
    """)
```

---

## 六、L4 — 知识记忆 (Knowledge Memory)

跨 Agent、跨用户的平台级知识库。

| 维度 | L3 情节记忆 | L4 知识记忆 |
|------|-----------|-----------|
| 范围 | 单个 Agent | 平台全局 |
| 来源 | 对话自动提取 | 手动配置 / 文档导入 |
| 示例 | "用户喜欢简洁回答" | "公司产品定价策略文档" |
| 更新 | 自动衰减 | 主动管理 |
| 检索 | 语义搜索 | 语义 + 关键词 + 命名空间 |

```python
class MemoryOrchestrator:
    def __init__(self, l2_memory, l3_store, l4_store):
        self.l2 = l2_memory
        self.l3 = l3_store
        self.l4 = l4_store

    async def build_context(self, agent_id, session_id, user_input, system_prompt):
        l3_memories = await self.l3.retrieve(agent_id, user_input)
        l4_memories = await self.l4.retrieve_global(user_input)
        memory_context = self._format_memories(l3_memories, l4_memories)
        enhanced_prompt = f"{system_prompt}\n\n{memory_context}"
        conversation = await self.l2.get_context(session_id)
        return enhanced_prompt, conversation
```

---

## 七、多 Agent 场景的记忆共享

```python
class MemoryPolicy(Enum):
    PRIVATE = "private"
    SHARED = "shared"
    GLOBAL = "global"
```

---

## 八、工程考量

### 性能优化

| 场景 | 策略 |
|------|------|
| pgvector 检索延迟 | 建 HNSW 索引 (m = 16, ef_construction = 200) |
| 大量对话并发 | Redis 做 L2，不查 DB |
| 记忆提取开销 | 异步 Celery/ARQ 任务，不阻塞用户 |
| 频繁检索 | Redis 缓存热点记忆（30min TTL） |

```sql
CREATE INDEX ON episodic_memories
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 200);
```

### 存储估算

```
假设 100 个 Agent，每天 1000 次会话
每次提取 2 条记忆，1536 维 embedding = 6KB
日增量: ~14MB，年增量: ~5GB
HNSW 索引额外 30%: ~6.5GB/年
```

---

## 九、记忆系统总览表

| 层级 | 名称 | 存储 | 生命周期 | 检索方式 | 作用 |
|------|------|------|---------|---------|------|
| L1 | 工作记忆 | LangGraph State + Checkpointer | 单次执行 | 直接读取 | 运行时状态流转 |
| L2 | 会话记忆 | Redis List + 摘要 | 24h TTL | 按时间排序 | 对话上下文连贯 |
| L3 | 情节记忆 | pgvector | 衰减/过期 | 语义相似度 + 重要性加权 | 跨会话知识复用 |
| L4 | 知识记忆 | pgvector + JSONB | 永久 | 语义 + 关键词 + 命名空间 | 平台级知识库 |

---

## 十、API 接口

```
POST   /api/v1/memories/{agent_id}/extract    手动触发记忆提取
GET    /api/v1/memories/{agent_id}            查询 Agent 的长期记忆列表
GET    /api/v1/memories/{agent_id}/search     语义搜索记忆
DELETE /api/v1/memories/{agent_id}            清除 Agent 所有长期记忆
DELETE /api/v1/memories/{agent_id}/{mem_id}   删除单条记忆
PUT    /api/v1/memories/{agent_id}/{mem_id}   更新记忆
POST   /api/v1/knowledge                      创建知识条目
GET    /api/v1/knowledge                      知识列表
GET    /api/v1/knowledge/search               搜索知识
DELETE /api/v1/knowledge/{id}                 删除知识条目
```

---

## 附录：名词对照

| 英文 | 中文 |
|------|------|
| Working Memory | 工作记忆 |
| Conversation Memory | 会话记忆 |
| Episodic Memory | 情节记忆 |
| Knowledge Memory | 知识记忆 |
| pgvector | PostgreSQL 向量检索扩展 |
| HNSW | 分层可导航小世界图 |
| Checkpoint | LangGraph 的状态快照 |
| RAG | 检索增强生成 |
| TTL | 生存时间 |
