from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RBACMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        if not hasattr(request.state, "user"):
            return await call_next(request)

        user = request.state.user
        path = request.url.path
        method = request.method

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
