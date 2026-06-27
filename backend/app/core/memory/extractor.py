import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.memory.episodic import EpisodicMemoryStore
from app.core.prompts.memory_prompts import MEMORY_EXTRACTION_PROMPT


class MemoryExtractor:
    def __init__(self, db: AsyncSession, llm=None):
        self.db = db
        self.llm = llm
        self.episodic_store = EpisodicMemoryStore(db)

    async def extract_from_conversation(
        self,
        agent_id: str,
        session_id: str,
        messages: List[Dict[str, Any]],
        importance: float = 0.5,
    ) -> int:
        if not messages:
            return 0

        combined = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}"
            for m in messages[-20:]
        )

        extracted_count = 0

        if self.llm:
            try:
                prompt = MEMORY_EXTRACTION_PROMPT.format(messages=combined)
                result = await self.llm.ainvoke(prompt)
                extracted = self._parse_extraction_result(result.content)
                for item in extracted:
                    await self.episodic_store.store(
                        agent_id=agent_id,
                        session_id=session_id,
                        content=item["content"],
                        memory_type=item.get("type", "user_fact"),
                        importance=item.get("importance", importance),
                    )
                    extracted_count += 1
            except Exception:
                pass

        if extracted_count == 0:
            await self.episodic_store.store(
                agent_id=agent_id,
                session_id=session_id,
                content=combined[:2000],
                memory_type="user_fact",
                importance=importance,
                raw_messages={"messages": messages[-10:]},
            )
            extracted_count = 1

        return extracted_count

    def _parse_extraction_result(self, text: str) -> list:
        try:
            json_start = text.find("[")
            json_end = text.rfind("]")
            if json_start >= 0 and json_end > json_start:
                return json.loads(text[json_start:json_end + 1])
        except (json.JSONDecodeError, KeyError):
            pass
        return []
