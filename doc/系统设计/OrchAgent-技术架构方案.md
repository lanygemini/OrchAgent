# OrchAgent — 技术架构方案

---

## 项目定位

基于 Python + LangGraph 的 OrchAgent，支持多 Agent 工作流定义、MCP 协议工具集成、DAG 可视化编排、实时执行监控和四层记忆系统。与已有 Java 项目（Spring AI interview-guide）形成 Python/Java 双技术栈互补，展示全面的 AI 应用开发能力。

---

## 相关设计文档

本方案为核心架构总览。以下各专项设计单独成文：

| 文档 | 说明 | 优先级 |
|------|------|--------|
| [记忆系统设计](OrchAgent-记忆系统设计.md) | L1~L4 四层记忆系统完整设计 | 高 |
| [错误处理与重试策略](OrchAgent-错误处理与重试策略.md) | 错误分类、重试退避、熔断降级、超时控制 | 高 |
| [认证与权限设计](OrchAgent-认证与权限设计.md) | JWT 认证、RBAC 权限、API Key 管理、资源隔离 | 高 |
| [Token 成本控制与管理](OrchAgent-Token成本控制与管理.md) | 成本估算、预算控制、用量统计、省钱策略 | 中 |
| [异步任务系统设计](OrchAgent-异步任务系统设计.md) | ARQ 任务队列、定时任务、长时间执行 | 中 |
| [工具沙箱安全设计](OrchAgent-工具沙箱安全设计.md) | 静态分析、Docker 隔离、输出过滤 | 中 |
| [可观测性设计](OrchAgent-可观测性设计.md) | 结构化日志、Prometheus 指标、链路追踪 | 中 |
| [安全加固清单](OrchAgent-安全加固清单.md) | HTTPS、Prompt注入、数据加密、供应链安全 | 中 |

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端层 (React)                        │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ │
│  │ Agent管理 │ │ 工具市场  │ │ 工作流编辑器│ │ 执行监控 │ │
│  │          │ │          │ │ (ReactFlow)│ │ (SSE日志)│ │
│  └──────────┘ └──────────┘ └────────────┘ └──────────┘ │
├─────────────────────────────────────────────────────────┤
│                    网关层 (Nginx)                        │
├─────────────────────────────────────────────────────────┤
│                    API 层 (FastAPI)                      │
│  ┌──────────────────────────────────────────────┐      │
│  │  REST: CRUD  │  SSE: 流式输出  │  WebSocket   │      │
│  └──────────────────────────────────────────────┘      │
├─────────────────────────────────────────────────────────┤
│                    核心引擎层                             │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐             │
│  │ Agent引擎 │ │ 工具系统  │ │ 工作流引擎  │             │
│  │ LangChain│ │ MCP+SPI  │ │  LangGraph  │             │
│  └──────────┘ └──────────┘ └────────────┘             │
├─────────────────────────────────────────────────────────┤
│                    基础设施层                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │PostgreSQL│ │  Redis   │ │  MinIO   │ │ LLM API  │  │
│  │(元数据)  │ │(缓存/状态)│ │(文件存储)│ │(多模型)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 二、技术栈明细

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **语言** | Python | 3.12+ | 主力开发语言 |
| **Web框架** | FastAPI | 0.115+ | REST API + SSE |
| **ASGI** | Uvicorn | 0.34+ | 异步服务器 |
| **Agent框架** | LangGraph | 0.4+ | 有状态工作流引擎 |
| **LLM抽象** | LangChain | 0.3+ | 统一多模型调用 |
| **MCP** | mcp | 1.x+ | 模型上下文协议 |
| **ORM** | SQLAlchemy 2.0 | 2.0+ | 异步数据库操作 |
| **数据库** | PostgreSQL + pgvector | 16+ | 元数据 + 向量存储 |
| **缓存** | Redis | 7+ | 执行状态缓存、Pub/Sub |
| **序列化** | Pydantic v2 | 2.x | 数据校验与序列化 |
| **迁移** | Alembic | 1.14+ | 数据库版本管理 |
| **前端** | React | 18 | UI框架 |
| **DAG可视化** | React Flow | 12+ | 工作流拖拽编排 |
| **状态管理** | Zustand | 5+ | 前端状态 |
| **部署** | Docker Compose | 3.8+ | 容器编排 |

---

## 三、数据库设计

### ER 图（核心表）

```
┌──────────────┐       ┌──────────────┐
│   agents     │       │    tools     │
├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │
│ name         │       │ name         │
│ role         │       │ type (ENUM)  │   ┌──────────────┐
│ llm_provider │       │ tool_schema  │   │ mcp_servers  │
│ model_name   │       │ config(JSON) │   ├──────────────┤
│ temperature  │       │ is_active    │   │ id (PK)      │
│ system_prompt│       │ created_at   │   │ name         │
│ max_tokens   │       └──────┬───────┘   │ transport    │
│ owner_id     │              │           │ command/url  │
│ created_at   │              │           │ env_vars     │
└──────┬───────┘              │           │ is_active    │
       │                      │           └──────────────┘
       │    ┌─────────────────┼──────────────────┐
       │    │                 │                  │
┌──────▼────▼───┐    ┌───────▼───────┐  ┌───────▼────────┐
│  workflows    │    │ workflow_nodes│  │ agent_tool_ref │
├───────────────┤    ├───────────────┤  ├────────────────┤
│ id (PK)       │    │ id (PK)       │  │ id (PK)        │
│ name          │    │ workflow_id   │  │ agent_id (FK)  │
│ description   │    │ type (ENUM)   │  │ tool_id (FK)   │
│ status        │    │ label         │  │ enabled        │
│ created_at    │    │ config(JSON)  │  └────────────────┘
└───────┬───────┘    │ position_x    │
        │            │ position_y    │
        │            │ agent_id (FK) │
        │            │ tool_id (FK)  │
        │            └───────┬───────┘
        │                    │
        │            ┌───────▼────────┐
        │            │ workflow_edges │
        │            ├────────────────┤
        │            │ id (PK)        │
        │            │ workflow_id    │
        │            │ source_node_id │
        │            │ target_node_id │
        │            │ condition_expr │
        │            │ label          │
        │            └────────────────┘
        │
┌───────▼────────────┐    ┌──────────────────┐
│ workflow_executions│    │  execution_steps  │
├────────────────────┤    ├──────────────────┤
│ id (PK)            │    │ id (PK)          │
│ workflow_id (FK)   │    │ execution_id (FK)│
│ status (ENUM)      │    │ node_id (FK)     │
│ state_snapshot(JSON│    │ step_type (ENUM) │
│ input_data (JSON)  │    │ input_data (JSON)│
│ output_data (JSON) │    │ output_data (JSON│
│ token_usage (JSON) │    │ status (ENUM)    │
│ error_message      │    │ error_message    │
│ started_at         │    │ token_usage      │
│ completed_at       │    │ started_at       │
│ created_by         │    │ completed_at     │
└────────────────────┘    └──────────────────┘
```

### L3/L4 记忆表

```
┌──────────────────────────────────┐
│       episodic_memories (L3)    │
├──────────────────────────────────┤
│ id (PK)                         │
│ agent_id (FK)                   │
│ session_id                      │
│ content: TEXT                   │
│ raw_messages: JSON              │
│ embedding: VECTOR(1536)         │
│ memory_type: ENUM               │
│ importance: FLOAT (0~1)         │
│ access_count: INT               │
│ created_at                      │
│ last_accessed_at                │
│ ttl_days: INT (nullable)        │
│ is_active: BOOL                 │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│      knowledge_memories (L4)     │
├──────────────────────────────────┤
│ id (PK)                         │
│ namespace: VARCHAR               │
│ key: VARCHAR                     │
│ content: TEXT                    │
│ content_type: VARCHAR            │
│ embedding: VECTOR(1536)         │
│ metadata: JSONB                 │
│ version: INT                    │
│ created_at                      │
│ updated_at                      │
└──────────────────────────────────┘
```

### 关键枚举定义

```python
class ToolType(str, Enum):
    BUILTIN = "builtin"
    MCP = "mcp"
    CUSTOM = "custom"

class NodeType(str, Enum):
    START = "start"
    END = "end"
    AGENT = "agent"
    TOOL = "tool"
    CONDITION = "condition"
    PARALLEL_FORK = "fork"
    PARALLEL_JOIN = "join"
    HUMAN = "human"

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class MemoryPolicy(str, Enum):
    PRIVATE = "private"
    SHARED = "shared"
    GLOBAL = "global"

class MemoryType(str, Enum):
    USER_FACT = "user_fact"
    PREFERENCE = "preference"
    DECISION = "decision"
    TOOL_RESULT = "tool_result"
```

---

## 四、核心模块详细设计

### 4.1 Agent 引擎

```
┌──────────────────────────────────────────┐
│              AgentManager                │
├──────────────────────────────────────────┤
│  create(config: AgentConfig) → Agent     │
│  get(id) → Agent                        │
│  list(filters) → List[Agent]            │
│  update(id, config) → Agent             │
│  delete(id)                             │
├──────────────────────────────────────────┤
│           Agent (运行时实例)              │
├──────────────────────────────────────────┤
│  agent_id: str                          │
│  config: AgentConfig                    │
│  llm: ChatModel  ← LangChain 统一封装   │
│  tools: List[BaseTool]                  │
│  memory: ConversationBufferMemory       │
├──────────────────────────────────────────┤
│  invoke(input) → AgentResponse          │
│  stream(input) → AsyncIterator[Chunk]    │
└──────────────────────────────────────────┘
```

**AgentConfig（Pydantic Schema）**：

```python
class AgentConfig(BaseModel):
    name: str
    role: str
    llm_provider: Literal["openai", "deepseek", "qwen", "zhipu"]
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str
    enable_memory: bool = True
    memory_window: int = 10
    memory_policy: MemoryPolicy = MemoryPolicy.PRIVATE
    shared_memory_namespaces: List[str] = []
    allowed_tools: List[str] = []
```

**LLM Provider 统一封装**：

```python
LLM_PROVIDER_MAP = {
    "openai":   ("langchain_openai", "ChatOpenAI"),
    "deepseek": ("langchain_community", "ChatDeepSeek"),
    "qwen":     ("langchain_community", "ChatTongyi"),
    "zhipu":    ("langchain_community", "ChatZhipuAI"),
}
```

### 4.2 工具系统 & MCP 集成

#### 工具分层架构

```
┌────────────────────────────────────────────────────┐
│                   ToolRegistry                     │
│  ┌──────────────────────────────────────────────┐ │
│  │          BaseTool (抽象基类)                   │ │
│  │  name / description / args_schema            │ │
│  │  _run(input) → str                           │ │
│  │  _arun(input) → Coroutine[str]               │ │
│  └──────────────┬───────────────────────────────┘ │
│         ┌───────┼───────┬───────────────┐         │
│  ┌──────▼──┐ ┌──▼───┐ ┌─▼──────┐ ┌─────▼──────┐ │
│  │Builtin  │ │ MCP  │ │Custom  │ │ Composite │ │
│  │Tool     │ │ Tool │ │Tool    │ │ Tool      │ │
│  │(计算器) │ │(协议)│ │(自定义)│ │ (组合)    │ │
│  │(搜索)   │ │      │ │        │ │           │ │
│  └─────────┘ └──────┘ └────────┘ └───────────┘ │
└────────────────────────────────────────────────────┘
```

#### MCP 集成设计

```
┌──────────────────────────────────────────────────┐
│              MCP Manager                         │
├──────────────────────────────────────────────────┤
│  管理 MCP Server 生命周期                         │
│                                                  │
│  register_server(config: MCPServerConfig)        │
│  discover_tools(server_id) → List[ToolDef]       │
│  create_tool_wrapper(server_id, tool_name)       │
│       → LangChain BaseTool                      │
│  health_check(server_id) → bool                  │
│                                                  │
│  支持 3 种传输方式:                               │
│  ├─ stdio: 子进程启动 MCP Server                 │
│  ├─ sse: HTTP SSE 长连接                        │
│  └─ streamable-http: 无状态 HTTP                │
└──────────────────────────────────────────────────┘
```

**MCPServerConfig**：

```python
class MCPServerConfig(BaseModel):
    name: str
    transport: Literal["stdio", "sse", "streamable-http"]
    command: Optional[str] = None
    args: List[str] = []
    env: Dict[str, str] = {}
    url: Optional[str] = None
    headers: Dict[str, str] = {}
    auth_type: Literal["none", "bearer", "oauth2"] = "none"
    auth_config: Optional[Dict] = None
```

**MCP -> LangChain Tool 桥接层**：

```python
class MCPToolWrapper(BaseTool):
    name: str
    description: str
    args_schema: Type[BaseModel]
    mcp_client: Any

    def _run(self, **kwargs) -> str:
        result = asyncio.run(self._arun(**kwargs))
        return result

    async def _arun(self, **kwargs) -> str:
        async with self.mcp_client as session:
            result = await session.call_tool(self.name, arguments=kwargs)
            return json.dumps(result.content)
```

### 4.3 工作流引擎 (LangGraph)

#### 编译流程

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 前端 DAG JSON │ →   │ Workflow     │ →   │ LangGraph    │
│ (React Flow) │     │ Compiler     │     │ StateGraph   │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                    ┌───────▼────────┐
                    │  1. DAG 校验   │
                    │  2. 拓扑排序   │
                    │  3. 节点映射   │
                    │  4. 边映射     │
                    │  5. 编译       │
                    └────────────────┘
```

#### LangGraph State 设计

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

#### 工作流编译器核心逻辑

```python
class WorkflowCompiler:
    def compile(self, dag: DAGDefinition) -> StateGraph:
        graph = StateGraph(AgentState)
        graph.add_node("__start__", self._noop)
        graph.add_node("__end__", self._noop)

        for node in dag.nodes:
            handler = self._get_node_handler(node.type)
            graph.add_node(node.id, handler)

        for edge in dag.edges:
            if edge.condition:
                graph.add_conditional_edges(
                    edge.source,
                    self._make_router(edge.condition),
                    self._get_branch_map(edge)
                )
            else:
                graph.add_edge(edge.source, edge.target)

        graph.set_entry_point(dag.start_node_id)
        return graph.compile()

    def _get_node_handler(self, node_type: NodeType):
        handlers = {
            NodeType.AGENT: self._handle_agent_node,
            NodeType.TOOL: self._handle_tool_node,
            NodeType.CONDITION: self._handle_condition_node,
            NodeType.PARALLEL_FORK: self._handle_fork,
            NodeType.HUMAN: self._handle_human_node,
        }
        return handlers[node_type]

    async def _handle_agent_node(self, state: AgentState) -> AgentState:
        agent = self.agent_registry.get(state["current_node"])
        llm = self.llm_factory.create(agent.config)
        memories = await self.memory_store.retrieve(
            agent_id=agent.id,
            query=state["context"].get("user_input", ""),
        )
        state["retrieved_memories"] = memories
        enhanced_prompt = self._inject_memories_to_prompt(
            agent.config.system_prompt, memories
        )
        tools = self.tool_registry.get_for_agent(agent.id)
        llm_with_tools = llm.bind_tools(tools)
        response = await llm_with_tools.ainvoke(state["messages"])
        if response.tool_calls:
            state["pending_tool_calls"] = response.tool_calls
        return {"messages": [response]}
```

### 4.4 执行引擎

#### 执行流程

```
POST /workflows/{id}/execute
│
├─ 1. 创建 execution 记录 (status=pending)
├─ 2. 编译 DAG -> LangGraph Runnable
├─ 3. 启动后台任务 (asyncio.Task)
│   ├─ 4. 遍历执行各节点
│   │   ├─ Agent Node -> L3/L4 记忆检索 -> LLM 调用 -> SSE 推送
│   │   ├─ Tool Node  -> 工具执行 -> SSE 推送
│   │   ├─ Condition  -> 条件求值 -> 路由
│   │   └─ Human Node -> 暂停 -> 等待用户输入
│   ├─ 5. 每个 Step 记录到 execution_steps
│   ├─ 6. 统计 token 用量
│   └─ 7. 完成 -> 异步提取 L3 新记忆
│
└─ 返回 execution_id（客户端通过 SSE 订阅实时日志）
```

#### SSE 流式输出设计

```python
class ExecutionStreamer:
    async def stream_execution(self, execution_id: str) -> AsyncIterator[str]:
        redis_channel = f"execution:{execution_id}"
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(redis_channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    event = json.loads(message["data"])
                    yield f"event: {event['type']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
        finally:
            await pubsub.unsubscribe(redis_channel)
```

**SSE 事件类型**：

```python
class SSEEventType:
    EXECUTION_STARTED = "execution.started"
    STEP_STARTED = "step.started"
    LLM_THINKING = "llm.thinking"
    LLM_COMPLETE  = "llm.complete"
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    MEMORY_RETRIEVED = "memory.retrieved"
    PATH_UPDATE = "path.update"
    STATE_SNAPSHOT = "state.snapshot"
    HUMAN_INPUT_REQUIRED = "human.required"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"
```

### 模块相关设计文档

- Agent 调用安全和重试：[错误处理与重试策略](OrchAgent-错误处理与重试策略.md)
- 工具沙箱隔离：[工具沙箱安全设计](OrchAgent-工具沙箱安全设计.md)
- 长时间工作流执行：[异步任务系统设计](OrchAgent-异步任务系统设计.md)
- Token 预算控制：[Token 成本控制与管理](OrchAgent-Token成本控制与管理.md)

---

## 五、记忆系统架构

平台采用四层记忆架构：L1 工作记忆（LangGraph State + Checkpointer）、L2 会话记忆（Redis 滑动窗口 + Token 预算 + 自动摘要）、L3 情节记忆（pgvector 语义检索 + 时间衰减）、L4 知识记忆（跨 Agent 平台级知识库）。

> 完整设计见 **[记忆系统设计文档](OrchAgent-记忆系统设计.md)**

### 与其它设计的交叉引用

记忆系统的异步提取依赖 **[异步任务系统](OrchAgent-异步任务系统设计.md)**，定时清理依赖定时任务调度，记忆检索的性能监控依赖 **[可观测性设计](OrchAgent-可观测性设计.md)**。

---

## 六、API 设计

### 完整 API 路由

```
POST   /api/v1/agents                         创建 Agent
GET    /api/v1/agents                         列表
GET    /api/v1/agents/{id}                    详情
PUT    /api/v1/agents/{id}                    更新
DELETE /api/v1/agents/{id}                    删除
POST   /api/v1/agents/{id}/test               Agent 单轮对话测试

POST   /api/v1/tools                          注册工具
GET    /api/v1/tools                          工具列表
GET    /api/v1/tools/{id}                     工具详情
DELETE /api/v1/tools/{id}                     删除工具
POST   /api/v1/tools/{id}/test                工具测试

POST   /api/v1/mcp/servers                    注册 MCP Server
GET    /api/v1/mcp/servers                    MCP Server 列表
GET    /api/v1/mcp/servers/{id}               详情
GET    /api/v1/mcp/servers/{id}/tools         发现该 Server 的工具列表
POST   /api/v1/mcp/servers/{id}/import        导入选中工具
DELETE /api/v1/mcp/servers/{id}               删除
GET    /api/v1/mcp/servers/{id}/health        健康检查

POST   /api/v1/workflows                      创建工作流
GET    /api/v1/workflows                      工作流列表
GET    /api/v1/workflows/{id}                 详情（含 DAG JSON）
PUT    /api/v1/workflows/{id}                 更新
DELETE /api/v1/workflows/{id}                 删除
POST   /api/v1/workflows/{id}/validate        校验 DAG 有效性

POST   /api/v1/workflows/{id}/execute         执行工作流
GET    /api/v1/workflows/{id}/executions      执行历史
GET    /api/v1/executions/{id}                执行详情
GET    /api/v1/executions/{id}/stream         SSE 实时流
GET    /api/v1/executions/{id}/steps          所有 Step 日志
POST   /api/v1/executions/{id}/pause          暂停
POST   /api/v1/executions/{id}/resume         恢复
POST   /api/v1/executions/{id}/cancel         取消

POST   /api/v1/memories/{agent_id}/extract    手动触发记忆提取
GET    /api/v1/memories/{agent_id}            查询 Agent 的长期记忆
DELETE /api/v1/memories/{agent_id}            清除 Agent 所有长期记忆
GET    /api/v1/memories/{agent_id}/search     语义搜索记忆

GET    /api/v1/stats/dashboard                仪表盘统计
```

### 关键 API 数据结构

```python
class ExecuteRequest(BaseModel):
    input_text: str
    variables: Optional[Dict[str, Any]] = {}
    stream: bool = True

class ExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    workflow_name: str
    status: ExecutionStatus
    input_data: Dict
    output_data: Optional[Dict]
    token_usage: TokenUsage
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    step_count: int

class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_estimate: float = 0.0
```

### API 相关设计文档

- 认证鉴权、RBAC 权限模型：[认证与权限设计](OrchAgent-认证与权限设计.md)
- API 限流策略：[认证与权限设计](OrchAgent-认证与权限设计.md)（速率限制章节）
- Token 成本追踪 API：[Token 成本控制与管理](OrchAgent-Token成本控制与管理.md)

---

## 七、项目目录结构

```
orchagent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   └── v1/
│   │   │       ├── agents.py
│   │   │       ├── tools.py
│   │   │       ├── mcp.py
│   │   │       ├── workflows.py
│   │   │       ├── executions.py
│   │   │       ├── memories.py
│   │   │       └── stats.py
│   │   ├── core/
│   │   │   ├── agent/
│   │   │   ├── tool/
│   │   │   ├── workflow/
│   │   │   ├── execution/
│   │   │   └── memory/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── mcp_servers/
│   │   │   └── nl2sql/
│   │   └── db/
│   ├── alembic/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── stores/
│   │   └── App.tsx
│   ├── package.json
│   └── tailwind.config.ts
├── docker-compose.yml
├── nginx.conf
└── README.md
```

---

## 八、前端工作流编辑器设计（React Flow）

### 自定义节点类型

```typescript
const nodeTypes = {
  agent: AgentNode,         // 蓝色圆角矩形
  tool: ToolNode,           // 绿色圆角矩形
  condition: ConditionNode, // 菱形
  start: StartNode,         // 圆形
  end: EndNode,             // 圆形
  fork: ForkNode,           // 六边形
  join: JoinNode,           // 六边形
  human: HumanNode,         // 橙色
};
```

---

## 九、部署架构

```yaml
services:
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
  api:
    build: ./backend
    env_file: .env
    depends_on: [postgres, redis]
  frontend:
    build: ./frontend
  postgres:
    image: pgvector/pgvector:pg16
  redis:
    image: redis:7-alpine
  arq_worker:
    build: ./backend
    command: arq arq_worker.WorkerSettings
  arq_scheduler:
    build: ./backend
    command: arq arq_scheduler.SchedulerSettings
```

> 完整部署含 ARQ Worker、Prometheus、Grafana、Jaeger 等服务，见 [异步任务系统设计](OrchAgent-异步任务系统设计.md) 和 [可观测性设计](OrchAgent-可观测性设计.md)。安全配置见 [安全加固清单](OrchAgent-安全加固清单.md)。

---

## 十、开发里程碑

| 里程碑 | 交付物 | 周期 |
|--------|--------|------|
| **M1: 脚手架** | FastAPI 项目 + 数据库 + Alembic + Agent CRUD + 认证体系 | 1 周 |
| **M2: LLM 集成** | LLM Factory + 多模型切换 + 流式 SSE + 错误处理 | 1.5 周 |
| **M3: 工具系统** | Tool Base + Registry + 内置工具 + Function Calling + 工具沙箱 | 1.5 周 |
| **M4: MCP 集成** | MCP Manager + Bridge + NL2SQL MCP Server | 1.5 周 |
| **M5: 记忆系统** | L2 会话记忆 + L3 情节记忆 + 异步任务 | 1.5 周 |
| **M6: 工作流引擎** | DAG 编译 + LangGraph Runner + 执行追踪 + 成本控制 | 2 周 |
| **M7: 前端** | React Flow 编辑器 + 执行监控页面 + SSE 对接 + 用量仪表盘 | 2 周 |
| **M8: 可观测性** | structlog + Prometheus + Grafana + Jaeger | 1 周 |
| **M9: 安全加固** | Prompt注入防护 + 输出过滤 + 审计日志 + 安全扫描 | 0.5 周 |
| **M10: 部署上线** | Docker Compose + Nginx + 云服务器 | 1 周 |

**总计约 13 周**

> 各里程碑的详细设计见对应的专项设计文档。

---

## 十一、面试亮点提炼清单

| 亮点 | 面试话术 |
|------|---------|
| **LangGraph 有状态工作流** | "基于 LangGraph 实现了有状态的 Agent 编排，支持 Checkpoint、断点续跑、人工干预" |
| **MCP 协议集成** | "接入了 MCP 协议，支持 stdio/sse/streamable-http 三种传输，把外部服务标准化为 Agent 工具" |
| **DAG 编译器** | "自研了 DAG -> LangGraph 的编译器，支持拓扑排序、环形检测、条件路由和并行分支" |
| **NL2SQL MCP 工具** | "把 NL2SQL 封装成 MCP Server，增加 SQL 安全校验（白名单+只读+超时）" |
| **四层记忆系统** | "L1 工作记忆 / L2 会话记忆 / L3 情节记忆 / L4 知识记忆，L3 实现自动提取->存储->检索->衰减" |
| **多模型适配** | "工厂模式封装 5+ LLM 供应商，一套接口切换 OpenAI/DeepSeek/千问/智谱" |
| **熔断与降级** | "LLM 调用带熔断器，超时自动降级到备用模型或本地 Ollama" |
| **Token 成本控制** | "实时追踪每次调用的 Token 消耗和费用，多级预算控制，超额自动降级" |
| **工具沙箱安全** | "自定义工具跑在 Docker 沙箱中，静态分析 + 容器隔离 + 输出脱敏三重防护" |
| **Python+Java双栈** | "Agent 平台用 Python + LangGraph 发挥 AI 生态优势，后端服务用 Spring Boot" |
