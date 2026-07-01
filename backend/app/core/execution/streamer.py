"""SSE 流式输出器：向客户端推送执行事件（Redis Pub/Sub 主通道 + asyncio.Queue 本地快速路径）"""
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
    """执行事件流——Redis Pub/Sub 为主通道，asyncio.Queue 为本地快速路径和回退"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._redis = None
        self._queues: Dict[str, asyncio.Queue] = {}  # execution_id → Queue（本地快速路径）

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

    async def _get_queue(self, execution_id: str) -> asyncio.Queue:
        if execution_id not in self._queues:
            self._queues[execution_id] = asyncio.Queue()
        return self._queues[execution_id]

    async def publish(self, execution_id: str, event_type: str, data: Any):
        """发布事件到本地缓冲区 + Redis Pub/Sub（双写确保多 worker 可达）"""
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 本地 Queue（同进程快速路径）
        queue = await self._get_queue(execution_id)
        await queue.put(message)

        # Redis Pub/Sub（跨 worker 广播）
        redis = await self._get_redis()
        if redis is not None:
            try:
                await redis.publish(f"execution:{execution_id}", json.dumps(message, ensure_ascii=False))
            except Exception:
                pass

    async def publish_end(self, execution_id: str):
        """发送流结束信号（双写）"""
        queue = await self._get_queue(execution_id)
        await queue.put(None)

        redis = await self._get_redis()
        if redis is not None:
            try:
                await redis.publish(f"execution:{execution_id}", json.dumps({"type": "end", "data": None}))
            except Exception:
                pass

    async def subscribe(self, execution_id: str) -> AsyncIterator[str]:
        """订阅执行事件流（SSE 格式）——优先从 Redis Pub/Sub 读取，回退到本地 Queue"""
        channel = f"execution:{execution_id}"
        redis = await self._get_redis()

        if redis is not None:
            # Redis 可用：订阅 Pub/Sub 作为主通道
            try:
                pubsub = redis.pubsub()
                await pubsub.subscribe(channel)

                # 先回放本地 Queue 中已有的事件（可能包含 subscribe 之前发出的）
                queue = await self._get_queue(execution_id)
                while not queue.empty():
                    try:
                        message = queue.get_nowait()
                        if message is None:
                            await pubsub.unsubscribe(channel)
                            return
                        yield f"event: {message['type']}\ndata: {json.dumps(message['data'], ensure_ascii=False)}\n\n"
                    except asyncio.QueueEmpty:
                        break

                # 从 Redis Pub/Sub 持续读取
                while True:
                    try:
                        raw = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=30)
                    except asyncio.TimeoutError:
                        # 发送心跳防止连接超时
                        yield ": heartbeat\n\n"
                        continue

                    if raw is None:
                        continue

                    if raw.get("type") == "message":
                        payload = raw.get("data")
                        if isinstance(payload, bytes):
                            payload = payload.decode("utf-8")

                        try:
                            message = json.loads(payload)
                        except (json.JSONDecodeError, TypeError):
                            continue

                        if message.get("type") == "end":
                            await pubsub.unsubscribe(channel)
                            return

                        if "type" in message and "data" in message:
                            yield f"event: {message['type']}\ndata: {json.dumps(message['data'], ensure_ascii=False)}\n\n"

            except Exception:
                # Redis 订阅失败，回退到本地 Queue
                async for event in self._subscribe_from_queue(execution_id):
                    yield event
            finally:
                try:
                    await pubsub.unsubscribe(channel)
                except Exception:
                    pass
        else:
            # Redis 不可用：仅从本地 Queue 读取（单 worker 模式）
            async for event in self._subscribe_from_queue(execution_id):
                yield event

    async def _subscribe_from_queue(self, execution_id: str) -> AsyncIterator[str]:
        """从本地 asyncio.Queue 读取事件（单 worker 回退模式）"""
        queue = await self._get_queue(execution_id)

        # 先回放缓冲区
        while not queue.empty():
            try:
                message = queue.get_nowait()
                if message is None:
                    return
                yield f"event: {message['type']}\ndata: {json.dumps(message['data'], ensure_ascii=False)}\n\n"
            except asyncio.QueueEmpty:
                break

        # 实时接收
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                if message is None:
                    return
                yield f"event: {message['type']}\ndata: {json.dumps(message['data'], ensure_ascii=False)}\n\n"
        finally:
            self.cleanup(execution_id)

    def cleanup(self, execution_id: str):
        """清理执行对应的队列"""
        self._queues.pop(execution_id, None)
