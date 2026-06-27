"""SSE 流式输出器：向客户端推送执行事件（asyncio.Queue 缓冲 + Redis Pub/Sub 备选）"""
import json
import asyncio
from typing import Any, AsyncIterator, Dict
from datetime import datetime, timezone


try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class ExecutionStreamer:
    """执行事件流——使用 asyncio.Queue 缓存事件，前端订阅后不会丢失"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._redis = None
        self._queues: Dict[str, asyncio.Queue] = {}  # execution_id → Queue

    async def _get_queue(self, execution_id: str) -> asyncio.Queue:
        if execution_id not in self._queues:
            self._queues[execution_id] = asyncio.Queue()
        return self._queues[execution_id]

    async def _get_redis(self):
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
        """发布事件到缓冲区，同时尝试 Redis Pub/Sub（多 worker 场景）"""
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        queue = await self._get_queue(execution_id)
        await queue.put(message)

        redis = await self._get_redis()
        if redis is not None:
            try:
                await redis.publish(f"execution:{execution_id}", json.dumps(message))
            except Exception:
                pass

    async def publish_end(self, execution_id: str):
        """发送流结束信号"""
        queue = await self._get_queue(execution_id)
        await queue.put(None)

    async def subscribe(self, execution_id: str) -> AsyncIterator[str]:
        """订阅执行事件流（SSE 格式）——先回放缓冲区再实时接收，收到结束信号后关闭"""
        queue = await self._get_queue(execution_id)

        while not queue.empty():
            try:
                message = queue.get_nowait()
                if message is None:
                    return
                yield f"event: {message['type']}\ndata: {json.dumps(message['data'], ensure_ascii=False)}\n\n"
            except asyncio.QueueEmpty:
                break

        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                except asyncio.TimeoutError:
                    break
                if message is None:
                    return
                yield f"event: {message['type']}\ndata: {json.dumps(message['data'], ensure_ascii=False)}\n\n"
        finally:
            self.cleanup(execution_id)

    def cleanup(self, execution_id: str):
        """清理执行对应的队列"""
        self._queues.pop(execution_id, None)
