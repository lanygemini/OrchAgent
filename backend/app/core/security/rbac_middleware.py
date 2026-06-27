"""RBAC 权限中间件：基于角色和权限控制 API 访问"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

RESOURCE_PATHS = {
    "/api/v1/agents": "agent",
    "/api/v1/tools": "tool",
    "/api/v1/workflows": "workflow",
    "/api/v1/executions": "execution",
    "/api/v1/mcp": "mcp",
    "/api/v1/memories": "memory",
    "/api/v1/stats": "stats",
}

PERMISSION_MAP = {
    "GET": "read",
    "POST": "write",
    "PUT": "write",
    "DELETE": "delete",
}


class RBACMiddleware(BaseHTTPMiddleware):
    """基于角色的访问控制中间件 — 检查用户是否有权执行操作"""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json", "/metrics"):
            return await call_next(request)

        if not hasattr(request.state, "user"):
            return await call_next(request)

        user = request.state.user
        path = request.url.path
        method = request.method

        for prefix, resource in RESOURCE_PATHS.items():
            if path.startswith(prefix):
                required = PERMISSION_MAP.get(method)
                if not required:
                    break
                perm = f"{required}:{resource}"
                if perm not in user.permissions and "admin" not in user.roles:
                    return JSONResponse(status_code=403, content={"detail": "权限不足"})
                break

        return await call_next(request)
