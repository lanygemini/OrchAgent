from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.memory import KnowledgeMemory


class KnowledgeMemoryStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(
        self,
        namespace: str,
        key: str,
        content: str,
        content_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> KnowledgeMemory:
        result = await self.db.execute(
            select(KnowledgeMemory).where(
                KnowledgeMemory.namespace == namespace,
                KnowledgeMemory.key == key,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.content = content
            existing.content_type = content_type
            existing.metadata = metadata or {}
            existing.embedding = embedding
            existing.version += 1
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            km = KnowledgeMemory(
                namespace=namespace,
                key=key,
                content=content,
                content_type=content_type,
                metadata=metadata or {},
                embedding=embedding,
                version=1,
            )
            self.db.add(km)
            await self.db.flush()
            await self.db.refresh(km)
            return km

    async def retrieve(
        self,
        query: str,
        namespace: Optional[str] = None,
        top_k: int = 5,
    ) -> List[KnowledgeMemory]:
        stmt = select(KnowledgeMemory)
        if namespace:
            stmt = stmt.where(KnowledgeMemory.namespace == namespace)
        stmt = stmt.order_by(KnowledgeMemory.version.desc()).limit(top_k)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete(self, namespace: str, key: str):
        from sqlalchemy import delete as sa_delete
        await self.db.execute(
            sa_delete(KnowledgeMemory).where(
                KnowledgeMemory.namespace == namespace,
                KnowledgeMemory.key == key,
            )
        )
