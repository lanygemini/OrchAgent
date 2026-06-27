"""资源所有者中间件：识别请求中的资源 ID 和类型，供后续权限校验使用"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class ResourceOwnerMiddleware(BaseHTTPMiddleware):
    """从 URL 路径中提取资源 ID 和类型注入 request.state"""

    async def dispatch(self, request: Request, call_next):
        if not hasattr(request.state, "user"):
            return await call_next(request)

        user = request.state.user
        path = request.url.path

        if path.startswith("/api/v1/agents/") and request.method in ("PUT", "DELETE"):
            resource_id = path.split("/")[-1]
            request.state.resource_id = resource_id
            request.state.resource_type = "agent"

        return await call_next(request)
