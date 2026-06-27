"""ARQ Worker 配置：定义工作进程的 Redis 连接和注册函数"""
from arq.connections import RedisSettings
from app.config import settings


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url, database=1)
    functions = ["app.tasks.tasks.cleanup_memories", "app.tasks.tasks.sync_token_usage", "app.tasks.tasks.extract_memories"]
    max_jobs: int = 20
    job_timeout: int = 3600
    keep_result: int = 3600
    health_check_interval: int = 30
