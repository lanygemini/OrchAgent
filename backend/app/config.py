from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "dev"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://orchagent:orchagent@localhost:5432/orchagent"
    database_sync_url: str = "postgresql://orchagent:orchagent@localhost:5432/orchagent"

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-this-to-a-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    openai_api_key: str = ""
    deepseek_api_key: str = ""
    qwen_api_key: str = ""
    zhipu_api_key: str = ""

    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
