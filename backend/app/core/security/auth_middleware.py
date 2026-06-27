from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security.jwt_service import jwt_service


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json", "/api/v1/auth/register", "/api/v1/auth/login"):
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
