"""ARQ 定时调度器配置：定时任务的 cron 定义"""
from arq import cron
from arq.connections import RedisSettings
from app.config import settings


class SchedulerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url, database=2)
    cron_jobs = [
        # 每天凌晨 3 点执行记忆清理
        cron(app.tasks.tasks.cleanup_memories)(hour=3, minute=0),
        # 每 5 分钟同步一次 Token 用量
        cron(app.tasks.tasks.sync_token_usage)(minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]
    job_timeout = 3600
