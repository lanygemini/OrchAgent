from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from app.config import settings

redis_pool: ArqRedis = None


async def init_arq():
    global redis_pool
    redis_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))


async def close_arq():
    global redis_pool
    if redis_pool:
        await redis_pool.close()


async def get_arq() -> ArqRedis:
    return redis_pool
