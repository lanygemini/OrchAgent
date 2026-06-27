from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.core.memory.episodic import EpisodicMemoryStore
from app.core.memory.extractor import MemoryExtractor


async def cleanup_memories(ctx: dict) -> dict:
    async with async_session_factory() as db:
        store = EpisodicMemoryStore(db)
        await store.decay(decay_factor=0.95)
        await store.cleanup()
        await db.commit()
    return {"status": "done", "task": "cleanup_memories", "timestamp": datetime.now(timezone.utc).isoformat()}


async def sync_token_usage(ctx: dict) -> dict:
    return {"status": "done", "task": "sync_token_usage", "timestamp": datetime.now(timezone.utc).isoformat()}


async def extract_memories(ctx: dict, agent_id: str, session_id: str, messages: list) -> dict:
    async with async_session_factory() as db:
        extractor = MemoryExtractor(db)
        count = await extractor.extract_from_conversation(
            agent_id=agent_id,
            session_id=session_id,
            messages=messages,
        )
        await db.commit()
    return {"status": "done", "task": "extract_memories", "agent_id": agent_id, "extracted": count}
