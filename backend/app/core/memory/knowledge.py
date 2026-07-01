"""知识记忆存储：持久化的结构化知识库（支持版本管理 + pgvector 语义检索）"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy import delete as sa_delete

from app.models.memory import KnowledgeMemory

# 尝试导入 pgvector 支持
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False


class KnowledgeMemoryStore:
    """知识记忆存储器 — 管理持久化的结构化知识（支持 upsert）"""

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
        """创建或更新知识条目（存在则更新版本号）"""
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
            existing.meta = metadata or {}
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
                meta=metadata or {},
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
        query_embedding: Optional[List[float]] = None,
    ) -> List[KnowledgeMemory]:
        """检索知识条目（优先 pgvector 语义检索，回退到版本降序）

        Args:
            query: 查询文本
            namespace: 命名空间过滤
            top_k: 返回数量
            query_embedding: 查询文本的向量嵌入（若提供则使用 pgvector 语义检索）
        """
        # 优先使用向量语义检索
        if query_embedding and PGVECTOR_AVAILABLE:
            try:
                embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
                namespace_clause = "AND namespace = :namespace" if namespace else ""
                stmt = text(f"""
                    SELECT *, (embedding <=> :query_vec::vector) AS distance
                    FROM knowledge_memories
                    WHERE embedding IS NOT NULL
                    {namespace_clause}
                    ORDER BY distance ASC
                    LIMIT :top_k
                """)
                params: Dict[str, Any] = {
                    "query_vec": embedding_str,
                    "top_k": top_k,
                }
                if namespace:
                    params["namespace"] = namespace
                result = await self.db.execute(stmt, params)
                rows = result.fetchall()
                memories = []
                for row in rows:
                    mem = await self.db.get(KnowledgeMemory, row.id)
                    if mem:
                        memories.append(mem)
                if memories:
                    return memories
            except Exception:
                pass

        # 回退：按版本降序
        stmt = select(KnowledgeMemory)
        if namespace:
            stmt = stmt.where(KnowledgeMemory.namespace == namespace)
        stmt = stmt.order_by(KnowledgeMemory.version.desc()).limit(top_k)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete(self, namespace: str, key: str):
        """删除知识条目"""
        from sqlalchemy import delete as sa_delete
        await self.db.execute(
            sa_delete(KnowledgeMemory).where(
                KnowledgeMemory.namespace == namespace,
                KnowledgeMemory.key == key,
            )
        )
