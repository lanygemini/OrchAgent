"""定时任务定义：记忆衰减清理、Token 用量同步、记忆提取"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.core.memory.episodic import EpisodicMemoryStore
from app.core.memory.extractor import MemoryExtractor
from app.models.execution import WorkflowExecution
from app.models.token_usage import TokenUsageRecord


async def cleanup_memories(ctx: dict) -> dict:
    """定时任务：记忆衰减 + 清理过期记忆"""
    async with async_session_factory() as db:
        store = EpisodicMemoryStore(db)
        await store.decay(decay_factor=0.95)
        await store.cleanup()
        await db.commit()
    return {"status": "done", "task": "cleanup_memories", "timestamp": datetime.now(timezone.utc).isoformat()}


async def sync_token_usage(ctx: dict) -> dict:
    """定时任务：将执行记录中的 Token 用量同步到专用用量表"""
    synced = 0
    async with async_session_factory() as db:
        result = await db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.status.in_(["completed", "failed"]),
                WorkflowExecution.token_usage != {},
                WorkflowExecution.completed_at.isnot(None),
            )
        )
        executions = result.scalars().all()

        for ex in executions:
            stmt = select(TokenUsageRecord).where(TokenUsageRecord.execution_id == ex.id)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                continue

            token_data = ex.token_usage or {}
            record = TokenUsageRecord(
                user_id=ex.user_id,
                execution_id=ex.id,
                agent_id=token_data.get("agent_id"),
                provider=token_data.get("provider", ""),
                model=token_data.get("model", ""),
                prompt_tokens=token_data.get("prompt_tokens", 0),
                completion_tokens=token_data.get("completion_tokens", 0),
                total_tokens=token_data.get("total_tokens", 0),
                estimated_cost=token_data.get("estimated_cost", 0.0),
                created_at=ex.completed_at,
            )
            db.add(record)
            synced += 1

        await db.commit()
    return {"status": "done", "task": "sync_token_usage", "synced": synced, "timestamp": datetime.now(timezone.utc).isoformat()}


async def extract_memories(ctx: dict, agent_id: str, session_id: str, messages: list) -> dict:
    """后台任务：从对话中提取记忆"""
    async with async_session_factory() as db:
        extractor = MemoryExtractor(db)
        count = await extractor.extract_from_conversation(
            agent_id=agent_id,
            session_id=session_id,
            messages=messages,
        )
        await db.commit()
    return {"status": "done", "task": "extract_memories", "agent_id": agent_id, "extracted": count}
