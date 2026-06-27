"""SSE 流式输出器：通过 Redis Pub/Sub 向客户端推送执行事件"""
import json
from typing import Any, AsyncIterator, Optional, Dict
from datetime import datetime, timezone

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# SSE 事件类型常量
SSE_EVENTS = {
    "execution.started": "execution.started",
    "step.started": "step.started",
    "llm.thinking": "llm.thinking",
    "llm.complete": "llm.complete",
    "tool.call": "tool.call",
    "tool.result": "tool.result",
    "memory.retrieved": "memory.retrieved",
    "path.update": "path.update",
    "state.snapshot": "state.snapshot",
    "human.required": "human.required",
    "execution.completed": "execution.completed",
    "execution.failed": "execution.failed",
}


class ExecutionStreamer:
    """通过 Redis Pub/Sub 发布执行事件，前端通过 SSE 订阅"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        """懒加载 Redis 连接"""
        if not REDIS_AVAILABLE:
            return None
        if self._redis is None:
            try:
                from redis.asyncio import from_url
                self._redis = await from_url(self.redis_url)
            except Exception:
                return None
        return self._redis

    async def publish(self, execution_id: str, event_type: str, data: Any):
        """向指定 execution 的频道发布事件消息"""
        redis = await self._get_redis()
        if redis is None:
            return

        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await redis.publish(f"execution:{execution_id}", message)

    async def subscribe(self, execution_id: str) -> AsyncIterator[str]:
        """订阅指定 execution 的事件流（SSE 格式）"""
        redis = await self._get_redis()
        if redis is None:
            yield f"event: error\ndata: {json.dumps({'error': 'Redis not available'})}\n\n"
            return

        pubsub = redis.pubsub()
        await pubsub.subscribe(f"execution:{execution_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    event = json.loads(message["data"])
                    yield f"event: {event['type']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
        finally:
            await pubsub.unsubscribe(f"execution:{execution_id}")
