"""ARQ 连接池工具：初始化 / 关闭 / 获取 Redis 连接"""
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from app.config import settings

redis_pool: ArqRedis = None


async def init_arq():
    """初始化 ARQ Redis 连接池"""
    global redis_pool
    redis_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))


async def close_arq():
    """关闭 ARQ Redis 连接池"""
    global redis_pool
    if redis_pool:
        await redis_pool.close()


async def get_arq() -> ArqRedis:
    """获取 ARQ Redis 连接池实例"""
    return redis_pool
