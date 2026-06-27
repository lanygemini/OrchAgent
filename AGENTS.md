# OrchAgent — Agent Guide

## Dev quickstart

```powershell
# start everything
docker compose up -d

# backend only (requires postgres+redis running)
uvicorn app.main:app --reload --port 8000

# check health
curl http://localhost:8000/health

# API docs
http://localhost:8000/docs
```

## Architecture

```
FastAPI middleware stack: CORS → AuthMiddleware → RBACMiddleware
```

| Layer | Entrypoint | Notes |
|-------|-----------|-------|
| App | `backend/app/main.py` | `lifespan` auto-creates tables in dev mode |
| API | `backend/app/api/router.py` → `api/v1/*.py` | 8 modules: auth, agents, tools, mcp, workflows, executions, memories, stats |
| Core | `backend/app/core/*/` | agent, tool, workflow, execution, memory, security, observability, prompts |
| Models | `backend/app/models/*.py` | SQLAlchemy async, UUID PKs, `TimestampMixin` + `UUIDMixin` in `db/base.py` |
| DB | `backend/app/db/session.py` | `async_session_factory`, auto-commit via `get_db` dependency |
| Config | `backend/app/config.py` | `pydantic-settings`, reads `.env` |

Key singletons: `jwt_service`, `agent_manager`, `tool_registry`, `mcp_manager`, `logger`, `settings`.

## Important conventions

- **All user-facing text is Chinese** — API errors, tool names, descriptions, frontend labels
- **Middlewares require authentication by default** — except `/health`, `/docs`, `/auth/register`, `/auth/login`, `/auth/refresh`
- **System prompt templates** live in `core/prompts/system_prompts.py`; if an Agent has no `system_prompt`, one is auto-assigned based on its `role`
- **DB tables auto-create** in `dev` mode via `Base.metadata.create_all` on startup (not in prod — use Alembic)

## Database

- PostgreSQL 16 + pgvector extension (via `pgvector/pgvector:pg16`)
- Alembic migrations: `alembic revision --autogenerate -m "msg"` then `alembic upgrade head`
- Connection: `postgresql+asyncpg://orchagent:orchagent@localhost:5432/orchagent`

## Current state

- No tests written yet — project is in early implementation phase
- No `pyproject.toml` or `Makefile` — deps managed via `requirements.txt`
- No linter/formatter/typecheck config yet
- Frontend is skeletal (login + dashboard pages, React Flow custom nodes scaffolded)

## Gotchas

- `.env` is committed with dev defaults but **no real API keys** — LLM calls will fail until `OPENAI_API_KEY` etc. are set
- `langgraph.checkpoint.postgres` requires the postgres extension — ensure postgres service is healthy before starting API
- SSE streaming uses Redis Pub/Sub — requires Redis to be running
- All model IDs are UUID strings (`String(36)`), not auto-increment integers
