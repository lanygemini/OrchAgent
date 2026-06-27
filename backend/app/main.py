from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html

from app.config import settings
from app.api.router import api_router
from app.core.security.auth_middleware import AuthMiddleware
from app.core.security.rbac_middleware import RBACMiddleware
from app.db.session import engine
from app.db.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment == "dev":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="OrchAgent API",
    description="多 Agent 工作流编排平台",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)

app.add_middleware(AuthMiddleware)
app.add_middleware(RBACMiddleware)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "environment": settings.environment, "message": "服务运行正常"}
