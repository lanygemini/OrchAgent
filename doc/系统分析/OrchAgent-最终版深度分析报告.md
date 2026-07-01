# OrchAgent — 最终版深度分析报告

> 综合三次独立分析（架构审查 + 竞品对标 + 前端可用性审查），于 2026-06-28 定稿
> 结论性质：基于源码逐行核实，非推测

---

## 一、项目定位与技术栈

OrchAgent 是一个**基于 LangGraph 的多 Agent 工作流编排平台**，对标 Dify / Coze / Flowise / n8n 这类「可视化 Agent 编排」产品。技术选型现代且合理：

| 层 | 选型 | 评价 |
|---|---|---|
| 后端 | FastAPI + LangGraph + SQLAlchemy 2.0 async | 主流、正确 |
| 存储 | PostgreSQL + pgvector + Redis | 具备向量检索的底子 |
| 前端 | React 18 + React Flow 12 + Zustand | 画布编排的标准组合 |
| 部署 | Docker Compose + Nginx | 一键起得来 |

代码组织工整：`core/` 按 `agent / tool / workflow / execution / memory / security / observability` 分层，概念清晰、命名规范、中文注释完整。**作为架构骨架，其完成度与分层意识明显高于多数同类 demo。**

---

## 二、现有功能盘点（已落地）

### 2.1 模块实现状态

| 模块 | 实现状态 | 代码行数 | 评价 |
|------|---------|---------|------|
| **Agent 管理** | ✅ 基本可用 | ~155行 | AgentRuntime + AgentManager + LLMFactory 完整闭环，支持 4 个 LLM 供应商 |
| **LLM 工厂** | ✅ 基本可用 | ~96行 | 动态 import + 回退链，但缺少 Ollama 本地模型支持 |
| **工具系统** | ⚠️ 部分可用 | ~100行 | Registry + Calculator + DateTime，缺少 web_search / json_parser |
| **MCP 集成** | ⚠️ 部分可用 | ~250行 | Manager + Bridge + NL2SQL Server，但 stdio 发现工具返回空列表 |
| **工作流编译器** | ⚠️ 框架完整 | 286行 | DAG→LangGraph 编译，但 condition / fork / join / human 为占位实现 |
| **执行引擎** | ✅ 核心可用 | ~343行 | 异步执行 + SSE + 步骤记录，但 resume 是假恢复 |
| **记忆系统** | ⚠️ 部分可用 | ~250行 | L3 情节记忆可用，L2/L4 有骨架，L1 仅 4 行占位 |
| **安全体系** | ⚠️ 骨架级 | ~200行 | JWT 完整，prompt_guard / rbac / audit 都是骨架 |
| **可观测性** | ❌ 仅定义 | ~136行 | metrics / tracing / logging 仅定义了接口和占位符 |
| **前端** | ✅ 基本可用 | ~1500行 | 11 个页面 + ReactFlow 编辑器 + SSE 对接 |

### 2.2 设计文档 vs 实际实现对照

| 设计文档 | 承诺功能 | 实际实现 | 差距 |
|---------|---------|---------|------|
| 技术架构方案 | 全部模块 | Agent/LLM/Workflow 骨架 | 核心节点空壳 |
| 记忆系统设计 | L1~L4 四层 | L3 基础 CRUD，其余占位 | 70% 未实现 |
| 错误处理与重试 | RetryHandler + CircuitBreaker + FallbackManager | 有代码但未嵌入调用链 | 未集成 |
| 认证与权限设计 | JWT + RBAC + 资源隔离 | JWT 完整，RBAC 48 行骨架 | 权限未生效 |
| Token 成本控制 | BudgetController + CostCalculator | 126 行实现 | 相对完整 |
| 异步任务系统 | ARQ Worker + 定时任务 | 12+24 行配置 | 未接入业务 |
| 工具沙箱安全 | 静态分析 + Docker 隔离 + 输出脱敏 | 三层代码都有 | 未集成到执行链路 |
| 可观测性设计 | structlog + Prometheus + Jaeger | 仅定义，无采集 | 90% 未实现 |
| 安全加固清单 | HTTPS + Prompt 注入防护 + 审计 | prompt_guard 51 行骨架 | 未生效 |

> ⚠️ **总体病根**：很多模块「形态完整、链路未通」——类（class）写好了，但没有被执行主链路真正调用。详见第三节。

---

## 三、关键架构缺陷（已在代码中验证）

这些不是「待优化」，而是会导致核心卖点失效的真问题。

### 🔴 缺陷 1：Agent 没有真正的工具调用循环（ReAct loop 缺失）

**最严重的问题。** `AgentRuntime.invoke()`（`agent_manager.py:55-82`）做了 `bind_tools`，但调用后**只取 `result.content` 就返回了，完全忽略 `result.tool_calls`**——不执行工具、不把结果回灌、不二次调用 LLM。

```python
llm_with_tools = self.llm.bind_tools(self.tools)
result = llm_with_tools.invoke(messages, **invoke_kwargs)
return AgentResponse(content=result.content, ...)  # tool_calls 被丢弃
```

**后果：** Agent 节点本质上是「单轮 LLM 对话」。它能说「我想调用 calculator」，但永远不会真的调用。平台最核心能力——**Agent 自主使用工具**——目前不工作。工具只能通过画布上单独的 `tool` 节点被「硬编码」调用（`config` 写死参数），而非 Agent 智能决策。

### 🔴 缺陷 2：暂停/恢复是「假」的（未接 LangGraph checkpointer）

`engine.py:156` 用 `graph.compile()` 编译时**没有传 checkpointer**，尽管 `compiler.py:7` 导入了 `PostgresSaver` 却从未使用。

- `pause()` 只是 `task.cancel()` + 把状态改成 `paused`——执行直接被杀死，状态不保留
- `resume()` 只是把状态字段改回 `running`，**没有任何从断点继续执行的逻辑**
- `human` 节点设了 `needs_human_input=True`，但图不会 `interrupt`，会直接跑到底

**后果：** 人在回路（Human-in-the-loop）、长流程暂停续跑——这些宣传点全部不可用。

### 🔴 缺陷 3：fork / join 并行节点是空壳

`compiler.py:276-282` 三个 handler 全是 `pass`。`state.py` 里 `merge_tool_results` reducer 写好了，但 join 节点不做分支结果聚合、不汇总 token。**复杂并行编排无法真正落地。**

```python
async def _handle_condition_node(self, state, changes):
    pass  # 条件求值依赖 eval() 且无安全沙箱

async def _handle_fork_node(self, state, changes):
    pass  # 并行分支完全未实现

async def _handle_join_node(self, state, changes):
    pass  # 汇合逻辑空缺

async def _handle_human_node(self, state, changes):
    changes["needs_human_input"] = True  # 仅设标记，无真正暂停等待机制
```

**影响**：当前工作流只能跑通"线性 Agent→Tool"链路，任何包含条件分支、并行、人工干预的工作流都无法真正执行。

### 🔴 缺陷 4：记忆检索不是语义检索（pgvector 形同虚设）

`embedding` 列存在，但：

- `EpisodicMemoryStore.retrieve()` 按 `importance` 排序，`query` 参数**完全没用到**
- `KnowledgeMemoryStore.retrieve()` 按 `version` 排序，`query` 参数也没用到

```python
# backend/app/core/memory/episodic.py

async def retrieve(self, agent_id, query, top_k):
    # 仅按 importance 排序，完全忽略了 query 参数
    # 没有使用 pgvector 做 embedding 相似度检索
    result = await self.db.execute(
        select(EpisodicMemory)
        .where(EpisodicMemory.agent_id == agent_id, ...)
        .order_by(EpisodicMemory.importance.desc())
        .limit(top_k)
    )
```

**后果：** 底层亮点「pgvector 向量记忆」根本没做相似度查询。记忆检索退化成「按重要性/版本取 top_k」，与语义无关。

### 🔴 缺陷 5：多 Worker 下 SSE 会丢事件

`streamer.py` 用进程内 `asyncio.Queue` 存事件；`publish` 虽也往 Redis 发了一份，但 **`subscribe()` 只从本地 Queue 读，从不读 Redis**。生产环境（Nginx + 多 uvicorn worker / ARQ worker）下，执行在 worker A、SSE 订阅落到 worker B，前端就收不到事件。Redis Pub/Sub 写了一半。

### 🔴 缺陷 6：MCP 工具发现是空操作

```python
# backend/app/core/tool/mcp/manager.py

async def discover_tools(self) -> List[MCPToolDef]:
    return self._tools  # 始终返回空列表，因为 set_tools 从未被调用
```

MCP Server 启动后没有通过 MCP 协议真正 `list_tools`，`_tools` 始终为空列表。注册 MCP Server 后无法发现其提供的工具，整个 MCP 集成链路断裂。

### 🟠 缺陷 7：其他确认的问题

- **预算控制未挂载**：`BudgetController` 写好了，但 `_run_execution` 执行前从不调用 `check_budget()`，超预算照跑
- **`eval()` 跑条件表达式**（`compiler.py:129/146`）：缺少沙箱，是注入面（虽为创建者自定义）
- **零测试**：无 pytest、无 ruff/mypy、无 CI
- **无 Alembic 迁移**：`alembic/versions/` 为空，仅靠 dev 模式 `create_all`，生产无法演进 schema
- **工作流执行不流式输出 token**：workflow 用 `invoke`（整段返回），`stream` 能力只在 Agent 单测端点用，画布执行看不到 token 级流式
- **全局单例问题**：`tool_registry` / `agent_manager` / `mcp_manager` 都是模块级全局单例，无法隔离测试
- **MCP 工具调用每次重启进程**：`bridge.py` 每次调用 `_call_via_mcp_client` 都 `stdio_client()` 新建进程，不复用 session

### 🟠 缺陷 8：前端交互层严重缺失

**总体病根**：前端只做了「列表 + 基础表单壳子」，把真正决定可用性的那层交互全省略了：

| 功能 | 看起来有 | 实际缺的关键交互 |
|---|---|---|
| Agent 添加 | 完整表单 | ❌ 工具绑定、❌ provider/model 下拉、❌ 错误提示、❌ 试聊 |
| 工具注册 | 列表+tab | ❌ 注册表单（按钮是死的）、❌ 测试（按钮是死的） |
| 工作流编辑 | 画布拖拽 | ❌ 节点配置面板、❌ 条件编辑器、❌ 选 agent/tool、❌ 验证 |

#### Agent 编辑页（`AgentEditPage.tsx`）

- **❌ 没法给 Agent 绑定工具**：整个创建/编辑表单里完全没有「工具绑定」这一项。建出来的 Agent 只能纯聊天
- **❌ provider / model 是自由文本框**：后端 schema 卡死 `^(openai|deepseek|qwen|zhipu)$`，敲错一个字母就被 422 拒绝，而前端 `catch {}` 把错误吃掉了
- **❌ 前后端默认值不一致**：`model_name` 前端默认 `gpt-4` vs 后端 `gpt-4o-mini`；`enable_memory` 前端 `false` vs 后端 `true`；`memory_policy` 前端 `recent` vs 后端 `private`
- **❌ 没有「测试 Agent」入口**：后端有测试端点，前端编辑页没有「试聊」按钮

#### 工具页（`ToolListPage.tsx`）

- **❌「+ 注册工具」按钮无 onClick**：前端没有工具注册表单/弹窗，无法从 UI 注册任何工具
- **❌「测试」按钮同样是死的**：后端 `/tools/{id}/test` 写好了，前端没接
- **结论**：工具页目前只能看列表 + 删除。可用工具仅限后端预置的 calculator / datetime

#### 工作流编辑器（`WorkflowEditorPage.tsx`）

- **❌ 没有节点配置面板**：拖一个节点进画布后，没有任何地方能配置它
  - Agent 节点：`agent_id` 硬塞成 `agents[0].id`，想换别的 Agent？没有 UI
  - Tool 节点：`tool_id` 永远是 `null`，**工具节点 100% 会在运行时报「工具节点未配置 tool_id」**
  - 节点 label 拖进去后改不了
- **❌ 条件边靠 label 前缀 hack**：`condition_expr: e.label.startsWith('if ') ? e.label : null`，没有条件编辑器
- **❌ 节点类型只暴露 3 种**：左侧面板只有 `agent / tool / condition`，后端支持 8 种（缺 start / end / fork / join / human）
- **❌「验证」按钮没接**：后端有校验端点，前端没调
- **❌ 没有删除节点的 UI**、连线无合法性校验、用 `alert()` 报错

---

## 四、与开源竞品的核心差距

参照系：**Dify / Coze Studio / n8n / Flowise / LangFlow / Activepieces / CrewAI / AutoGen(AG2)**

### 4.1 对标产品矩阵

| 能力维度 | OrchAgent | Dify | Langflow | n8n | CrewAI |
|---------|-----------|------|----------|-----|--------|
| **可视化编辑器** | ReactFlow 基础版 | 拖拽式完整编辑器 | LangChain 组件拖拽 | 节点连线+代码切换 | 无（代码驱动） |
| **RAG / 知识库** | ❌ 无 | ✅ 完整（上传→分块→向量→检索→重排） | ✅ 内置向量检索组件 | ✅ 社区节点 | ❌ |
| **多模型支持** | 4 家国内+OpenAI | 20+ 供应商含 Ollama | 全 LangChain 生态 | 10+ 供应商 | 全 LangChain |
| **MCP 集成** | ⚠️ 骨架 | ✅ 深度集成 | ✅ 已支持 | 🔄 实验性 | ❌ |
| **工作流节点类型** | 8 种（4 种空壳） | 20+ 种完整节点 | 50+ LangChain 组件 | 400+ 集成节点 | 5 种角色类型 |
| **Human-in-the-loop** | ❌ 占位 | ✅ 审批/表单/对话 | ✅ 交互式节点 | ✅ 等待 Webhook | ❌ |
| **并行执行** | ❌ 未实现 | ✅ 并行节点 | ✅ 并行分支 | ✅ 并行节点 | ✅ 并行 Agent |
| **对话应用类型** | ❌ 仅工作流 | ✅ 对话/工作流/Agent 三种 | ✅ 多种 | ✅ 触发器+对话 | ✅ Agent |
| **API 发布** | ❌ 无 | ✅ 一键发布为 API | ✅ API 端点 | ✅ Webhook | ❌ |
| **模板市场** | ❌ 无 | ✅ 100+ 模板 | ✅ 社区模板 | ✅ 模板库 | ❌ |
| **多租户** | ❌ 单用户 | ✅ 企业级多租户 | ✅ 基础多租户 | ✅ 工作空间 | ❌ |
| **插件/扩展市场** | ❌ 无 | ✅ 插件体系 | ✅ 自定义组件 | ✅ 社区节点 | ✅ Tool 装饰器 |
| **日志/监控** | ❌ 占位 | ✅ 完整追踪 | ✅ LangSmith 集成 | ✅ 执行日志 | ✅ 回调系统 |
| **触发与集成生态** | ❌ 仅 API 手动触发 | ✅ Webhook/定时/事件 | ✅ 多种触发器 | ✅ 400+ 连接器 | ❌ |
| **部署** | Docker Compose | Docker / K8s / 云 | Docker | Docker / K8s | pip install |

### 4.2 🔴 核心差距（决定性缺陷）

#### 缺距 1：触发与集成生态（差距最大）

落地型产品的真正价值在「连接」。Dify / n8n / Activepieces 都有：
- **Webhook / 定时 / 事件触发器**（OrchAgent 只能 API 手动触发）
- **几百个预置连接器**（Slack / 飞书 / 数据库 / HTTP / 邮件…）。OrchAgent 内置工具只有 calculator + datetime 两个
- **HTTP Request / Code 通用节点**作为万能胶水

> OrchAgent 目前是「孤岛」：既进不来（无触发器），也出不去（无连接器）。这是与可落地产品最本质的距离。

#### 缺距 2：RAG / 知识库（几乎完全缺失）

Dify / Coze / Flowise 的核心场景是 RAG：文档上传 → 切分 → 向量化 → 检索增强。OrchAgent 有 pgvector 却**没有文档摄取管线、没有 embedding 生成、没有 retriever 节点**，记忆检索还不是语义的。对「企业知识助手」这个最大落地场景基本空白。

- **文档上传与解析**：PDF / Word / Markdown / HTML → 文本提取
- **智能分块**：按段落 / 语义 / 递归分块
- **向量化与索引**：Embedding → pgvector / Weaviate / Qdrant
- **检索策略**：向量相似度 + 关键词混合检索 + 重排序（Reranker）
- **知识库管理**：多知识库、权限隔离、增量更新

#### 缺距 3：Agent 自主性（被缺陷 #1 卡死）

CrewAI / AutoGen 的卖点是 multi-agent 协作 + 自主工具调用 + 角色分工。OrchAgent 的 Agent 连单体 ReAct 循环都没跑通，谈不上 agent 间协作、反思（reflection）、群聊（group chat）等高级模式。

#### 缺距 4：缺少对话式应用模式

Dify 支持三种应用类型：
- **聊天助手**：纯对话，RAG 增强
- **工作流**：DAG 编排
- **Agent**：自主决策 + 工具调用

OrchAgent 只有工作流模式。没有独立的"对话应用"——用户不能直接跟 Agent 聊天（虽然有 `/agents/{id}/test`，但只是单轮测试，不是持久化对话）。

#### 缺距 5：缺少应用发布能力

竞品都支持一键将工作流 / Agent 发布为：
- **API 端点**：外部系统直接调用
- **嵌入式聊天组件**：嵌入到第三方网页
- **Webhook 触发器**：事件驱动执行

OrchAgent 的工作流只能通过内部 API 触发，无法对外暴露为服务。

### 4.3 🟡 重要差距（影响竞争力）

#### 缺距 6：MCP 集成不完整

| 功能 | OrchAgent | 竞品 |
|------|-----------|------|
| 工具发现 | ❌ `discover_tools` 返回空 | Dify: 自动发现 + 导入 |
| SSE / HTTP 传输 | ❌ 仅 stdio 有基础支持 | 标准: 三种传输完整支持 |
| MCP 工具调用 | ⚠️ 每次调用重启进程 | 标准: 长连接复用 session |
| MCP 资源/提示词 | ❌ 仅工具 | 标准: tools + resources + prompts |

#### 缺距 7：没有模板系统

Dify 有 100+ 预置模板（客服、翻译、代码审查...），用户可以一键创建。OrchAgent 从零开始，没有任何模板或示例工作流。

#### 缺距 8：调试与可运维性

- 成熟产品有**单步调试 / 变量面板 / 节点级输入输出回放 / 运行回溯**；OrchAgent 有 StepRecord 落库，但调试体验和 checkpoint 回放缺失
- **可观测**：Dify 接 Langfuse，有完整 trace 树；OrchAgent 的 OTel 是 optional 静默降级，metrics / tracing / logging 从未被调用
- **版本管理 / 发布 / 灰度**：工作流有 `draft/published` 状态字段，但没有版本快照、回滚、A/B

#### 缺距 9：安全体系薄弱

| 安全特性 | OrchAgent | 竞品 |
|---------|-----------|------|
| RBAC 权限 | ❌ 48 行骨架 | Dify: 完整 RBAC + 资源隔离 |
| API Key 管理 | ❌ 无 | Dify: API Key 生成 / 轮换 / 限流 |
| 多租户隔离 | ❌ 无 | Dify: 命名空间隔离 |
| 审计日志 | ❌ 51 行骨架 | Dify: 完整操作审计 |
| 工具沙箱 | ⚠️ 有 Docker 沙箱代码 | 但未集成到工具执行链路 |

### 4.4 🟢 已有的亮点（值得保留和强化）

1. **四层记忆系统设计** — 概念上比多数竞品更精细（L1 工作 / L2 会话 / L3 情节 / L4 知识），但实现需要补全
2. **Token 成本控制** — BudgetController 有 126 行实现，包含日 / 周 / 月预算，这在国内产品中是差异化亮点
3. **MCP 协议集成** — 方向正确，Bridge 层设计合理，需要补完发现和调用
4. **NL2SQL MCP Server** — 有实际 SQL 安全校验，是独立的增值功能
5. **熔断降级** — CircuitBreaker + FallbackManager 有 178 行实现，竞品中少见
6. **工具沙箱三层防护** — 静态分析 + Docker 隔离 + 输出脱敏，架构设计完整，只差集成到执行链路

---

## 五、架构层面的反思

### 5.1 当前架构的局限

OrchAgent 的设计思路是"先设计后实现"（10 篇设计文档 → M1~M10 开发计划）。

这种方式的优点是文档完整、面试展示好，但缺点是 **设计与实现脱节严重**：

1. **设计文档描述了 100% 的功能，代码只实现了 30%**，且最核心的并行 / 条件 / 人工干预都是空壳
2. **过度设计**：四层记忆系统在概念上很漂亮，但 L1 只有 4 行、L2 的 Redis 滑动窗口完全没实现、L3 检索不用向量、L4 只写了 CRUD
3. **竞品都是自下而上生长的**：Dify 从聊天助手出发→加工作流→加 RAG→加 Agent；OrchAgent 试图一步到位，反而每一步都不深
4. **前端停留在「壳子」阶段**：列表 + 表单能跑，但决定可用性的关键交互（节点配置、工具绑定、条件编辑）全省略了，导致后端能力无法通过 UI 释放

### 5.2 竞品架构对比

| 维度 | OrchAgent | Dify | n8n |
|------|-----------|------|-----|
| 设计哲学 | 自顶向下（先设计后实现） | 自底向上（场景驱动迭代） | 自底向上（集成驱动） |
| 核心循环 | 工作流→Agent→Tool | 对话→RAG→工作流→Agent | 触发器→节点→集成 |
| 扩展方式 | 代码扩展 | 插件 + API | 社区节点 |
| 用户入口 | 工作流编辑器 | 对话界面 | 工作流编辑器 |
| 前端完成度 | 表单壳子，关键交互缺失 | 完整可交互 | 完整可交互 |

### 5.3 建议：收敛功能范围，做深核心场景

与其追求 10 篇设计文档的完整性，不如把以下 2-3 个场景做到真正端到端可用：

#### 场景 A："Agent + 工具 + RAG" 对话

```
用户上传文档 → 文档分块 + Embedding → 存入 pgvector
用户发起对话 → Agent 检索知识库 → 注入上下文 → LLM 生成回答
Agent 自动调用工具（计算器/搜索/MCP）→ 返回增强结果
```

#### 场景 B："条件分支工作流"

```
拖拽一个包含条件路由的工作流 → 真正按条件分叉执行 → 看到结果
支持并行分支 → 两个 Agent 同时处理 → 结果汇合
支持人工审批节点 → 暂停等待 → 用户批准后继续
```

#### 场景 C："MCP 工具即插即用"

```
注册 MCP Server → 自动发现工具 → 导入到平台
Agent 工作流中绑定 MCP 工具 → 执行时真正调用 → 返回结果
NL2SQL MCP Server 端到端可用
```

每个场景从 UI 到后端到数据库全链路打通，比 10 个半成品更有说服力。

---

## 六、优先修复建议

按 **影响度 × 实现难度** 排序，兼顾后端链路贯通与前端可用性。

### P0 — 不做就没有产品价值

| # | 任务 | 原因 | 预估工作量 | 涉及文件 |
|---|------|------|-----------|---------|
| 1 | **补全 Agent ReAct 循环** | 平台立身之本，Agent 必须能自主调用工具 | 1 周 | `agent_manager.py` |
| 2 | **补全工作流核心节点**：condition 真正求值、fork/join 并行执行、human 暂停/恢复 | 当前工作流无法端到端跑通任何非平凡场景 | 2-3 周 | `compiler.py`, `engine.py`, `state.py` |
| 3 | **接 LangGraph checkpointer** | 让 pause/resume/human-in-the-loop 真正工作 | 1 周 | `engine.py`, `workflow/state.py` |
| 4 | **SSE 改为真正读 Redis Pub/Sub** | 否则多 worker 生产环境直接不可用 | 0.5 周 | `streamer.py` |
| 5 | **前端节点配置面板** | 不补则整个工作流空转，后端能力无法通过 UI 释放 | 1.5 周 | `WorkflowEditorPage.tsx`, `NodePanel.tsx` |
| 6 | **前端工具注册弹窗 + Agent 工具绑定** | 工具页按钮全死，Agent 没法绑定工具 | 1 周 | `ToolListPage.tsx`, `AgentEditPage.tsx` |

### P1 — 影响竞争力

| # | 任务 | 原因 | 预估工作量 | 涉及文件 |
|---|------|------|-----------|---------|
| 7 | **实现 RAG 知识库**：文档上传→分块→Embedding→向量检索→注入 Prompt | 竞品标配，没有则无法处理知识密集型任务 | 2-3 周 | 新增 `core/rag/`, `api/v1/knowledge.py`, 前端 `KnowledgePage.tsx` |
| 8 | **记忆检索接入向量搜索** | pgvector cosine similarity 替代 importance 排序 | 1 周 | `memory/episodic.py`, `memory/knowledge.py` |
| 9 | **MCP 工具发现修复** | 通过 MCP 协议真正 `list_tools` | 1 周 | `mcp/manager.py`, `mcp/bridge.py` |
| 10 | **对话应用模式** | 持久化 Agent 对话 + RAG 注入 | 1.5 周 | 新增 `api/v1/chat.py`, 前端 `ChatPage.tsx` |
| 11 | **可观测性落地** | 至少接入 LangFuse 或 Prometheus 真正采集 | 1 周 | `observability/metrics.py`, `observability/tracing.py` |
| 12 | **预算检查前置** | `_run_execution` 执行前调用 `check_budget()` | 0.5 周 | `engine.py` |

### P2 — 从"能用"到"好用"

| # | 任务 | 原因 | 预估工作量 | 涉及文件 |
|---|------|------|-----------|---------|
| 13 | **前端 Agent 表单修复**：provider/model 下拉、错误提示、默认值对齐、试聊入口 | 用户体验基线 | 0.5 周 | `AgentEditPage.tsx` |
| 14 | **前端工作流补全**：条件编辑器、节点删除、连线校验、fork/join/human 节点、验证按钮 | 编辑器可用性 | 1 周 | `WorkflowEditorPage.tsx` |
| 15 | **触发器 + HTTP/Code 通用节点 + 高频连接器** | 打破孤岛 | 2 周 | 新增节点类型 + 连接器 |
| 16 | **工作流模板系统** | 5-10 个预置模板降低上手门槛 | 1 周 | 新增 `templates/`, 前端模板选择页 |
| 17 | **应用发布为 API** | 从内部工具变为平台 | 1 周 | 新增 `api/v1/published.py` |
| 18 | **RBAC + 多租户** | 生产部署必须 | 1.5 周 | `security/rbac_middleware.py` |
| 19 | **`eval` 换成受限表达式求值器** | 收敛注入面 | 0.5 周 | `compiler.py` |
| 20 | **补测试（pytest）、Alembic 迁移、ruff/mypy/CI** | 工程化基线 | 2 周 | 全项目 |

---

## 七、核心证据索引（便于复核）

### 后端缺陷

| 缺陷 | 文件:行 |
|---|---|
| Agent 丢弃 tool_calls | `backend/app/core/agent/agent_manager.py:69-82` |
| compile 无 checkpointer | `backend/app/core/execution/engine.py:156` |
| pause/resume 仅改状态 | `backend/app/core/execution/engine.py:305-342` |
| fork/join 空壳 | `backend/app/core/workflow/compiler.py:276-282` |
| episodic 检索不用 query | `backend/app/core/memory/episodic.py:45-70` |
| knowledge 检索不用 query | `backend/app/core/memory/knowledge.py:58-70` |
| SSE 只读本地 Queue | `backend/app/core/execution/streamer.py:62-85` |
| 条件 eval 无沙箱 | `backend/app/core/workflow/compiler.py:129,146` |
| MCP 工具发现未握手 | `backend/app/core/tool/mcp/manager.py:67-72` |
| 预算控制未挂载 | `backend/app/core/execution/engine.py`（`_run_execution` 中无 `check_budget` 调用） |
| MCP 每次调用新建进程 | `backend/app/core/tool/mcp/bridge.py:46-56` |

### 前端缺陷

| 缺陷 | 文件:行 |
|---|---|
| Agent 表单无工具绑定 | `frontend/src/pages/AgentEditPage.tsx`（全文无 tool 字段） |
| provider/model 自由文本 | `AgentEditPage.tsx:94-95` |
| 后端 provider 正则约束 | `backend/app/schemas/agent.py:12` |
| catch 吞错误 | `AgentEditPage.tsx:50` |
| 注册工具按钮无 onClick | `frontend/src/pages/ToolListPage.tsx:62` |
| 测试按钮无 onClick | `ToolListPage.tsx:44` |
| Agent 节点硬塞 agents[0] | `frontend/src/pages/WorkflowEditorPage.tsx:146` |
| Tool 节点 tool_id 恒为 null | `WorkflowEditorPage.tsx:153` |
| 条件边 label hack | `WorkflowEditorPage.tsx:84` |
| start/end 当 agent 渲染 | `WorkflowEditorPage.tsx:47` |
| 验证按钮无 onClick | `WorkflowEditorPage.tsx:195` |

---

## 八、总结

| 维度 | 评价 |
|------|------|
| **设计完整度** | ⭐⭐⭐⭐⭐ 10 篇专项设计文档，覆盖面广 |
| **实现完整度** | ⭐⭐ 核心模块 30% 可用，关键节点空壳 |
| **前端可用性** | ⭐ 列表+表单壳子，关键交互全缺，后端能力无法通过 UI 释放 |
| **与竞品差距** | 🔴 缺少 RAG、对话应用、触发器集成、应用发布四大核心能力 |
| **差异化亮点** | 🟢 四层记忆设计、Token 成本控制、NL2SQL MCP、熔断降级 |
| **最大风险** | Agent 无 ReAct 循环 + 工作流核心节点空壳 + 前端交互缺失 = 端到端跑不通 |

**定性**：OrchAgent 是一个**架构分层优秀、概念覆盖全面，但核心执行链路有多处「通电不通流」的早期骨架**。代码质量与模块设计意识高于多数同类项目，但距「可落地」还差在——很多关键模块停在「类已写好但未接入主链路」的状态，加上前端交互层大面积缺失、零测试，真实可用性存疑。

**一句话**：优先级应该是 **先让一条完整链路跑通**（Agent ReAct + 工作流条件/并行 + 前端节点配置），再扩展广度（RAG / 触发器 / 模板）。2-3 个端到端可用的场景，比 10 个半成品更有说服力。
