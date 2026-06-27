"""认证中间件：从 Authorization 请求头解析 JWT 并注入 request.state.user"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security.jwt_service import jwt_service


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT 认证中间件 — 白名单路径跳过，其余路径要求 Bearer Token"""

    async def dispatch(self, request: Request, call_next):
        # 白名单路径：无需认证
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json", "/metrics", "/api/v1/auth/register", "/api/v1/auth/login"):
            return await call_next(request)

        if request.url.path.startswith("/api/v1/auth/refresh"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "缺少或无效的 Authorization 请求头"})

        token = auth_header.split(" ", 1)[1]
        payload = jwt_service.decode_token(token)
        if payload is None:
            return JSONResponse(status_code=401, content={"detail": "令牌无效或已过期"})

        request.state.user = payload
        return await call_next(request)
