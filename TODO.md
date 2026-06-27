# 待完善问题清单

## 代码层面

### 1. 工作流节点处理器（compiler.py:190-200）
condition / fork / join 三个节点处理器仅透传状态（return state）。当前边路由（compile 方法）已覆盖基本功能，后续可增强：
- fork 节点：标记并行分支开始，复制状态快照
- join 节点：合并各分支的 tool_results、collected_memories，汇总 token_usage

### 2. 数据库迁移（alembic/versions/）
`alembic/versions/` 目录为空，无迁移文件。生产部署前需执行：
```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```
当前依赖 `Base.metadata.create_all`（仅 dev 模式生效）。

### 3. NL2SQL execute_query（mcp_servers/nl2sql/server.py:97）
`execute_query` 返回占位结果，未真正连接数据库执行 SQL。需接入真实 database URL 执行只读查询。

### 4. SQLAlchemy JSON 列 default 模式（models/）
以下文件使用 `default=dict` / `default=list` 而非 `default_factory=dict`：
- `models/workflow.py:30` — `config`
- `models/tool.py:14-15` — `tool_schema`, `config`
- `models/memory.py:34` — `meta`
- `models/mcp.py:17-18,20` — `args`, `env`, `headers`
- `models/execution.py:16,18,37` — JSON 列

虽 SQLAlchemy 对 JSON 列有特殊处理，改为 `default_factory` 更安全。

### 5. OpenTelemetry 追踪（core/observability/tracing.py）
`setup_tracing()` 在 OT 包未安装时静默返回，生产环境需安装 `opentelemetry-api`、`opentelemetry-sdk` 并配置导出器。

---

## 工程层面

### 6. 测试
项目当前零测试。建议配置：
- 单元测试：pytest + pytest-asyncio
- 集成测试：测试 API 端点 + 数据库操作
- 覆盖率：pytest-cov

### 7. Linter / Typecheck
无 `pyproject.toml`、`ruff`、`mypy` 配置。建议：
- 格式化：ruff format
- Lint：ruff check
- 类型检查：mypy --strict

### 8. 前端
前端仅完成登录页和仪表盘骨架（React Flow 自定义节点已搭建），其余页面待实现：
- Agent 列表/编辑页
- Tool 列表页
- Workflow 列表/编辑器页
- Execution 列表/详情页
- MCP 管理页
- Settings 设置页

### 9. .env API Keys
`.env` 中无真实 API Key（OPENAI_API_KEY 等为空），LLM 调用会失败。使用前需填入有效密钥。
