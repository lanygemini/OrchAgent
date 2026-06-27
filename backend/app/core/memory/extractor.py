"""记忆提取器：从对话中识别和提取值得长期记忆的信息"""
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.memory.episodic import EpisodicMemoryStore
from app.core.prompts.memory_prompts import MEMORY_EXTRACTION_PROMPT


class MemoryExtractor:
    """记忆提取器 — 使用 LLM 从对话中提取关键信息并存入情景记忆"""

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
        """从对话消息中提取记忆，返回提取数量"""
        if not messages:
            return 0

        combined = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}"
            for m in messages[-20:]  # 只取最近 20 条消息
        )

        extracted_count = 0

        # 如果配置了 LLM，则使用 LLM 提取结构化记忆
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

        # LLM 提取失败或无结果时，保存原始消息片段作为回退
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
        """从 LLM 返回文本中解析 JSON 数组"""
        try:
            json_start = text.find("[")
            json_end = text.rfind("]")
            if json_start >= 0 and json_end > json_start:
                return json.loads(text[json_start:json_end + 1])
        except (json.JSONDecodeError, KeyError):
            pass
        return []
