"""情景记忆存储：Agent 对话记忆的存取、衰减和清理"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete as sa_delete, or_

from app.models.memory import EpisodicMemory


class EpisodicMemoryStore:
    """情景记忆存储器 — 管理 Agent 的对话记忆"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def store(
        self,
        agent_id: str,
        content: str,
        memory_type: str = "user_fact",
        importance: float = 0.5,
        session_id: Optional[str] = None,
        raw_messages: Optional[Dict] = None,
        embedding: Optional[List[float]] = None,
        ttl_days: Optional[int] = None,
    ) -> EpisodicMemory:
        """存储一条情景记忆"""
        memory = EpisodicMemory(
            agent_id=agent_id,
            session_id=session_id,
            content=content,
            raw_messages=raw_messages,
            embedding=embedding,
            memory_type=memory_type,
            importance=importance,
            ttl_days=ttl_days,
            last_accessed_at=datetime.now(timezone.utc),
        )
        self.db.add(memory)
        await self.db.flush()
        await self.db.refresh(memory)
        return memory

    async def retrieve(
        self,
        agent_id: str,
        query: str,
        top_k: int = 5,
        min_importance: float = 0.0,
    ) -> List[EpisodicMemory]:
        """检索 Agent 的情景记忆（按重要性排序）"""
        result = await self.db.execute(
            select(EpisodicMemory)
            .where(
                EpisodicMemory.agent_id == agent_id,
                EpisodicMemory.is_active == True,
                EpisodicMemory.importance >= min_importance,
            )
            .order_by(EpisodicMemory.importance.desc())
            .limit(top_k)
        )
        memories = result.scalars().all()

        # 更新访问计数和时间
        for mem in memories:
            mem.access_count += 1
            mem.last_accessed_at = datetime.now(timezone.utc)

        return memories

    async def decay(self, decay_factor: float = 0.95):
        """对所有记忆进行重要性衰减（每次调用乘以衰减因子，防止记忆无限堆积）"""
        result = await self.db.execute(
            select(EpisodicMemory).where(EpisodicMemory.is_active == True)
        )
        memories = result.scalars().all()
        for mem in memories:
            mem.importance = max(0.0, mem.importance * decay_factor)

    async def cleanup(self):
        """清理过期的记忆（ttl_days 到期）"""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            sa_delete(EpisodicMemory).where(
                EpisodicMemory.ttl_days.isnot(None),
                EpisodicMemory.created_at < now - func.make_interval(days=EpisodicMemory.ttl_days),
            )
        )

    async def delete_by_agent(self, agent_id: str):
        """删除指定 Agent 的所有记忆"""
        await self.db.execute(
            sa_delete(EpisodicMemory).where(EpisodicMemory.agent_id == agent_id)
        )
