"""全局配置：从环境变量 / .env 文件加载"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 运行环境
    environment: str = "dev"
    debug: bool = True

    # 数据库连接
    database_url: str = "postgresql+asyncpg://orchagent:orchagent@localhost:5432/orchagent"
    database_sync_url: str = "postgresql://orchagent:orchagent@localhost:5432/orchagent"

    # Redis 连接（用于会话缓存和 SSE 事件发布）
    redis_url: str = "redis://localhost:6379/0"

    # JWT 认证配置
    jwt_secret: str = "change-this-to-a-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # LLM API 密钥
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    qwen_api_key: str = ""
    zhipu_api_key: str = ""

    # CORS 允许的前端来源
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
