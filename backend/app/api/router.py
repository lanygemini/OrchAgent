"""API 路由汇总 — 自动注册所有 V1 路由模块"""
from fastapi import APIRouter

from app.api.v1 import agents, tools, mcp, workflows, executions, memories, stats, auth

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(tools.router)
api_router.include_router(mcp.router)
api_router.include_router(workflows.router)
api_router.include_router(executions.router)
api_router.include_router(memories.router)
api_router.include_router(stats.router)
