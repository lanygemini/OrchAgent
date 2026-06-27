"""RBAC 权限中间件：基于角色和权限控制 API 访问"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RBACMiddleware(BaseHTTPMiddleware):
    """基于角色的访问控制中间件 — 检查用户是否有权执行操作"""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        if not hasattr(request.state, "user"):
            return await call_next(request)

        user = request.state.user
        path = request.url.path
        method = request.method

        # Agent 资源权限检查
        if method == "GET" and path.startswith("/api/v1/agents"):
            if "read:agent" not in user.permissions and "admin" not in user.roles:
                return JSONResponse(status_code=403, content={"detail": "权限不足"})

        if method in ("POST", "PUT") and path.startswith("/api/v1/agents"):
            if "write:agent" not in user.permissions and "admin" not in user.roles:
                return JSONResponse(status_code=403, content={"detail": "权限不足"})

        if method == "DELETE" and path.startswith("/api/v1/agents"):
            if "delete:agent" not in user.permissions and "admin" not in user.roles:
                return JSONResponse(status_code=403, content={"detail": "权限不足"})

        return await call_next(request)
