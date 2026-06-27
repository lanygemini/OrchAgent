"""资源所有者中间件：识别请求中的资源 ID 和类型，供后续权限校验使用"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

RESOURCE_PATTERNS = [
    ("/api/v1/agents/", "agent"),
    ("/api/v1/tools/", "tool"),
    ("/api/v1/workflows/", "workflow"),
    ("/api/v1/executions/", "execution"),
    ("/api/v1/mcp/servers/", "mcp_server"),
    ("/api/v1/memories/", "memory"),
]


class ResourceOwnerMiddleware(BaseHTTPMiddleware):
    """从 URL 路径中提取资源 ID 和类型注入 request.state"""

    async def dispatch(self, request: Request, call_next):
        if not hasattr(request.state, "user"):
            return await call_next(request)

        path = request.url.path

        for prefix, resource_type in RESOURCE_PATTERNS:
            if path.startswith(prefix) and request.method in ("PUT", "PATCH", "DELETE"):
                resource_id = path[len(prefix):].split("/")[0]
                if resource_id:
                    request.state.resource_id = resource_id
                    request.state.resource_type = resource_type
                    break

        return await call_next(request)
