# OrchAgent

基于 Python + LangGraph 的多 Agent 工作流编排平台。

## 技术栈

- **后端**: Python 3.12+, FastAPI, LangGraph, LangChain, SQLAlchemy 2.0, PostgreSQL + pgvector, Redis
- **前端**: React 18, React Flow 12+, Zustand, TypeScript, TailwindCSS
- **部署**: Docker Compose, Nginx

## 前置依赖

- **Python** 3.12+
- **Node.js** 20+ （前端开发）
- **Docker** + **Docker Compose** （PostgreSQL + Redis + 一键启动）
- **PostgreSQL 16** + pgvector 扩展（本地开发时需安装）
- **Redis 7** （会话缓存、SSE 事件、ARQ 任务队列）

## 快速启动（Docker 一键部署）

```bash
# 启动所有服务（PostgreSQL + Redis + API + 前端 + Nginx）
docker compose up -d

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

启动后访问：
- 后端 API 文档：http://localhost:8000/docs
- 前端页面：http://localhost:3000
- Nginx（反向代理入口）：http://localhost:80

## 本地开发启动

### 1. 启动基础设施

先使用 Docker 启动数据库和缓存：

```bash
docker compose up -d postgres redis
```

### 2. 后端启动

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器（热重载）
uvicorn app.main:app --reload --port 8000
```

后端默认配置从 `backend/.env` 读取，各配置项说明：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ENVIRONMENT` | 运行环境（dev/prod） | dev |
| `DATABASE_URL` | PostgreSQL 异步连接串 | postgresql+asyncpg://orchagent:orchagent@localhost:5432/orchagent |
| `REDIS_URL` | Redis 连接串 | redis://localhost:6379/0 |
| `JWT_SECRET` | JWT 签名密钥 | （生产环境必须修改） |
| `OPENAI_API_KEY` | OpenAI API 密钥 | （留空则无法调用对应 LLM） |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 同上 |
| `CORS_ORIGINS` | 允许的前端域名 | ["http://localhost:5173","http://localhost:3000"] |

> 开发模式下应用启动时会自动创建数据库表（`Base.metadata.create_all`），生产环境请使用 Alembic 迁移。

### 3. 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器（端口 3000，自动代理 /api 到后端）
npm run dev

# 构建生产版本
npm run build
```

前端开发服务器地址：http://localhost:3000

Vite 已配置 `/api` 路径代理到 `http://localhost:8000`，无需额外配置跨域。

### 4. 验证服务

```bash
# 后端健康检查
curl http://localhost:8000/health

# 预期响应
{"status":"ok","version":"0.1.0","environment":"dev","message":"服务运行正常"}
```

## 项目结构

```
OrchAgent/
├── backend/              后端 FastAPI 应用（核心代码）
├── frontend/             前端 React 应用
├── doc/                  设计文档
├── deploy/               部署脚本
├── docker-compose.yml    开发环境配置
├── docker-compose.prod.yml  生产环境配置
├── nginx.conf            Nginx 反向代理配置
└── OrchAgent/            （预留目录）
```

## 后端目录详解

```
backend/
├── app/
│   ├── main.py                    # 应用入口：FastAPI 初始化、中间件注册、健康检查
│   ├── config.py                  # 全局配置：从 .env 加载（数据库/Redis/JWT/LLM 密钥）
│   ├── dependencies.py            # FastAPI 依赖注入：数据库会话、用户认证、权限校验
│   │
│   ├── api/                       # API 层 —— HTTP 路由与请求处理
│   │   ├── router.py              # 路由汇总：自动注册所有 v1 子路由
│   │   └── v1/                    # API v1 版本（8 个模块）
│   │       ├── auth.py            # 认证 API：注册、登录、刷新令牌
│   │       ├── agents.py          # Agent CRUD：创建/查询/更新/删除/测试 Agent
│   │       ├── tools.py           # 工具管理：注册/查询/测试工具
│   │       ├── workflows.py       # 工作流管理：CRUD + DAG 校验
│   │       ├── executions.py      # 执行管理：触发执行、状态查询、SSE 流式输出
│   │       ├── mcp.py             # MCP 集成：注册 MCP 服务器、发现/导入工具
│   │       ├── memories.py        # 记忆管理：提取/查询/搜索/清除记忆
│   │       └── stats.py           # 统计面板：仪表盘汇总数据
│   │
│   ├── core/                      # 核心业务逻辑层
│   │   ├── agent/                 # Agent 运行时管理
│   │   │   ├── agent_manager.py   # Agent 管理器：从模型创建/缓存 Runtime，驱动 invoke/stream
│   │   │   └── llm_factory.py     # LLM 工厂：动态加载 OpenAI/DeepSeek/Qwen/Zhipu 等供应商
│   │   │
│   │   ├── execution/             # 工作流执行引擎
│   │   │   ├── engine.py          # 执行引擎：异步驱动 DAG 执行，支持暂停/恢复/取消
│   │   │   ├── streamer.py        # SSE 流式输出器：通过 Redis Pub/Sub 推送执行事件
│   │   │   ├── cost_control.py    # 成本控制：Token 费用估算、预算检查
│   │   │   └── error_handler.py   # 错误处理：重试策略（指数退避）、熔断器、降级管理
│   │   │
│   │   ├── workflow/              # 工作流 DAG 编译
│   │   │   ├── compiler.py        # 编译器：将 DAG 定义编译为 LangGraph StateGraph
│   │   │   └── state.py           # 状态定义：AgentState（节点间流转的数据载体）
│   │   │
│   │   ├── tool/                  # 工具系统
│   │   │   ├── base.py            # 工具基类：BuiltinTool / CustomTool / CompositeTool
│   │   │   ├── registry.py        # 注册中心：管理工具注册和 Agent 绑定关系
│   │   │   ├── builtin/           # 内置工具
│   │   │   │   ├── calculator.py  # 安全计算器（AST 白名单，防注入）
│   │   │   │   └── datetime_tool.py # 日期时间工具
│   │   │   ├── mcp/               # MCP（Model Context Protocol）集成
│   │   │   │   ├── manager.py     # MCP 服务管理器：启动/停止/健康检查
│   │   │   │   └── bridge.py      # MCP 桥接：将外部 MCP 工具包装为平台 BaseTool
│   │   │   └── sandbox/           # 代码沙箱（安全执行用户代码）
│   │   │       ├── docker_sandbox.py  # Docker 沙箱：隔离容器运行代码
│   │   │       ├── static_analyzer.py # 静态代码分析：检测危险模块/函数
│   │   │       └── output_filter.py   # 输出过滤：脱敏敏感信息
│   │   │
│   │   ├── memory/                # 记忆系统
│   │   │   ├── working.py         # 工作记忆状态（AgentState 复用）
│   │   │   ├── episodic.py        # 情景记忆：对话长期记忆的存取/衰减/清理
│   │   │   ├── session.py         # 会话记忆：基于 Redis 的短期对话缓存
│   │   │   ├── knowledge.py       # 知识记忆：结构化持久知识库（版本管理）
│   │   │   └── extractor.py       # 记忆提取器：LLM 驱动从对话中提取记忆
│   │   │
│   │   ├── security/              # 安全与认证
│   │   │   ├── jwt_service.py     # JWT 令牌服务：创建/解码/密码哈希
│   │   │   ├── auth_middleware.py  # 认证中间件：解析 JWT，白名单/保护路由
│   │   │   ├── rbac_middleware.py  # RBAC 中间件：基于角色的权限控制
│   │   │   ├── resource_owner_middleware.py # 资源所有者识别
│   │   │   ├── prompt_guard.py    # 提示防护：检测注入攻击，脱敏输出
│   │   │   └── audit.py           # 审计日志：记录用户操作
│   │   │
│   │   ├── observability/         # 可观测性
│   │   │   ├── logging.py         # 结构化日志（structlog，开发彩色/生产 JSON）
│   │   │   ├── metrics.py         # Prometheus 指标：LLM/工具/工作流/API 统计
│   │   │   └── tracing.py         # 分布式追踪（OpenTelemetry，可选）
│   │   │
│   │   └── prompts/               # 提示词模板
│   │       ├── system_prompts.py   # Agent 角色系统提示词（助手/客服/数据分析师等）
│   │       ├── memory_prompts.py   # 记忆提取/检索提示词
│   │       ├── workflow_prompts.py # 工作流条件评估/人工输入提示词
│   │       └── nl2sql_prompts.py   # 自然语言转 SQL 提示词
│   │
│   ├── models/                    # SQLAlchemy ORM 模型层
│   │   ├── agent.py               # Agent 模型（LLM 配置/记忆策略）
│   │   ├── user.py                # 用户与角色（RBAC 多对多关联）
│   │   ├── tool.py                # 工具注册
│   │   ├── workflow.py            # 工作流 DAG（WorkflowNode + WorkflowEdge）
│   │   ├── execution.py           # 执行记录与步骤日志
│   │   ├── memory.py              # 情景记忆 + 知识记忆
│   │   ├── mcp.py                 # MCP 服务器注册
│   │   └── token_usage.py         # Token 用量记录与预算
│   │
│   ├── schemas/                   # Pydantic Schema（请求/响应数据模型）
│   │   ├── agent.py               # Agent 创建/更新/响应/列表
│   │   ├── workflow.py            # 工作流 DAG 定义与校验
│   │   ├── execution.py           # 执行请求/响应/步骤
│   │   ├── tool.py                # 工具注册/测试
│   │   ├── mcp.py                 # MCP 服务器/工具定义
│   │   ├── memories.py            # 记忆搜索/知识记忆
│   │   └── stats.py               # 仪表盘统计
│   │
│   ├── db/                        # 数据库基础设施
│   │   ├── base.py                # ORM 基类（TimestampMixin / UUIDMixin）
│   │   └── session.py             # 异步引擎与会话工厂
│   │
│   ├── tasks/                     # 后台任务（ARQ 队列）
│   │   ├── tasks.py               # 任务函数：记忆清理/Token 同步/记忆提取
│   │   ├── arq_scheduler.py       # 定时调度器配置（cron 表达式）
│   │   ├── arq_worker.py          # Worker 配置
│   │   └── worker.py              # Redis 连接池管理
│   │
│   └── mcp_servers/               # 内置 MCP 服务器实现
│       └── nl2sql/                # NL2SQL 服务：自然语言→SQL（含安全校验）
│           └── server.py
│
├── alembic/                       # 数据库迁移（Alembic）
│   ├── env.py                     # 迁移环境配置
│   └── versions/                  # 迁移版本
│
├── Dockerfile                     # 后端 Docker 镜像构建
├── requirements.txt               # Python 依赖
└── .env                           # 环境变量（含 dev 默认值）
```

### 架构分层

各层职责清晰，依赖方向自上而下：

```
API 路由层 (api/)          → HTTP 请求/响应，参数校验
       ↓
核心业务层 (core/)         → Agent/执行/工具/记忆/安全/可观测
       ↓
数据模型层 (models/)       → SQLAlchemy ORM 定义
     ↙     ↘
Schema层   DB层
(schemas/) (db/)
```

- `api/` 层不包含业务逻辑，只做参数校验和结果封装
- `core/` 层封装所有业务逻辑，不感知 HTTP 细节
- `models/` + `db/` 层负责数据持久化
- `tasks/` 处理异步后台任务
- `mcp_servers/` 是实现 MCP 协议的内置子服务

## 许可证

MIT
