import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class SessionMemoryConfig:
    window_size: int = 10
    token_budget: int = 4096
    redis_url: str = "redis://localhost:6379/0"
    ttl_seconds: int = 3600


class SessionMemory:
    def __init__(self, session_id: str, config: Optional[SessionMemoryConfig] = None):
        self.session_id = session_id
        self.config = config or SessionMemoryConfig()
        self._redis = None

    async def _get_redis(self):
        if not REDIS_AVAILABLE:
            return None
        if self._redis is None:
            from redis.asyncio import from_url
            self._redis = await from_url(self.config.redis_url)
        return self._redis

    async def add_message(self, message: BaseMessage):
        redis = await self._get_redis()
        if redis is None:
            return

        key = f"session:{self.session_id}:messages"
        msg_data = json.dumps({
            "type": message.type,
            "content": message.content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await redis.rpush(key, msg_data)
        await redis.ltrim(key, -self.config.window_size, -1)
        await redis.expire(key, self.config.ttl_seconds)

    async def get_history(self) -> List[BaseMessage]:
        redis = await self._get_redis()
        if redis is None:
            return []

        key = f"session:{self.session_id}:messages"
        raw = await redis.lrange(key, 0, -1)
        messages = []
        for item in raw:
            data = json.loads(item)
            if data["type"] == "human":
                messages.append(HumanMessage(content=data["content"]))
            elif data["type"] == "ai":
                messages.append(AIMessage(content=data["content"]))
        return messages

    async def clear(self):
        redis = await self._get_redis()
        if redis is None:
            return
        key = f"session:{self.session_id}:messages"
        await redis.delete(key)

    async def estimate_tokens(self) -> int:
        history = await self.get_history()
        return sum(len(m.content) for m in history)

    async def needs_summary(self) -> bool:
        tokens = await self.estimate_tokens()
        return tokens > self.config.token_budget
