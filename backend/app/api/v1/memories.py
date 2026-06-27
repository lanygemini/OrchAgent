"""记忆 API：提取 / 查询 / 搜索 / 清除情景记忆，管理知识记忆"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional

from app.dependencies import get_db, get_current_user
from app.models.memory import EpisodicMemory, KnowledgeMemory
from app.schemas.memories import MemorySearchRequest, MemoryResponse, KnowledgeMemoryCreate, KnowledgeMemoryResponse

router = APIRouter(prefix="/api/v1/memories", tags=["Memories"])


@router.post("/{agent_id}/extract")
async def extract_memories(agent_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """从对话中提取记忆（实现待完成）"""
    return {"message": "记忆提取端点（实现待完成）", "agent_id": agent_id}


@router.get("/{agent_id}")
async def list_memories(
    agent_id: str,
    memory_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """查询 Agent 的情景记忆列表"""
    query = select(EpisodicMemory).where(EpisodicMemory.agent_id == agent_id)
    if memory_type:
        query = query.where(EpisodicMemory.memory_type == memory_type)
    query = query.order_by(EpisodicMemory.created_at.desc()).limit(100)
    result = await db.execute(query)
    memories = result.scalars().all()
    return {"items": [MemoryResponse.model_validate(m) for m in memories]}


@router.delete("/{agent_id}", status_code=204)
async def clear_memories(agent_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """清除 Agent 的所有情景记忆"""
    await db.execute(delete(EpisodicMemory).where(EpisodicMemory.agent_id == agent_id))


@router.get("/{agent_id}/search")
async def search_memories(
    agent_id: str,
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """搜索 Agent 的记忆（按重要性排序）"""
    result = await db.execute(
        select(EpisodicMemory).where(EpisodicMemory.agent_id == agent_id, EpisodicMemory.is_active == True)
        .order_by(EpisodicMemory.importance.desc()).limit(top_k)
    )
    memories = result.scalars().all()
    return {"items": [MemoryResponse.model_validate(m) for m in memories]}


@router.post("/knowledge")
async def create_knowledge(data: KnowledgeMemoryCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """创建知识记忆条目"""
    km = KnowledgeMemory(
        namespace=data.namespace,
        key=data.key,
        content=data.content,
        content_type=data.content_type,
        metadata=data.metadata,
    )
    db.add(km)
    await db.flush()
    await db.refresh(km)
    return km
