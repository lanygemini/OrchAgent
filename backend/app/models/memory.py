from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, JSON, Float, Integer, Boolean, DateTime
from app.db.base import Base, UUIDMixin, TimestampMixin
from datetime import datetime


class EpisodicMemory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "episodic_memories"

    agent_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_messages: Mapped[dict] = mapped_column(JSON, nullable=True)
    embedding: Mapped[list] = mapped_column(JSON, nullable=True)
    memory_type: Mapped[str] = mapped_column(String(16), default="user_fact")
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    ttl_days: Mapped[int] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class KnowledgeMemory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_memories"

    namespace: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), default="text")
    embedding: Mapped[list] = mapped_column(JSON, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
