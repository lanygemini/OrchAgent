# OrchAgent

基于 Python + LangGraph 的多 Agent 工作流编排平台。

## 技术栈

- **后端**: Python 3.12+, FastAPI, LangGraph, LangChain, SQLAlchemy 2.0, PostgreSQL + pgvector, Redis
- **前端**: React 18, React Flow 12+, Zustand, TypeScript, TailwindCSS
- **部署**: Docker Compose, Nginx

## 快速开始

```bash
docker compose up -d
```

API 文档：http://localhost:8000/docs

## 项目结构

```
backend/      后端 FastAPI 应用
frontend/     前端 React 应用
doc/          设计文档
docker-compose.yml  开发环境配置
```

## 许可证

MIT
