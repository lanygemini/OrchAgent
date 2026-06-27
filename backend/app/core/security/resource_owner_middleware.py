from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class ResourceOwnerMiddleware(BaseHTTPMiddleware):
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
