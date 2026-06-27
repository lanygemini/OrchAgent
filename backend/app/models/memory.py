"""记忆模型：情景记忆（对话记录）+ 知识记忆（持久知识库）"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, JSON, Float, Integer, Boolean, DateTime
from app.db.base import Base, UUIDMixin, TimestampMixin
from datetime import datetime


class EpisodicMemory(Base, UUIDMixin, TimestampMixin):
    """情景记忆 — Agent 从对话中提取的长期记忆"""
    __tablename__ = "episodic_memories"

    agent_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_messages: Mapped[dict] = mapped_column(JSON, nullable=True)
    embedding: Mapped[list] = mapped_column(JSON, nullable=True)       # 向量嵌入（用于语义检索）
    memory_type: Mapped[str] = mapped_column(String(16), default="user_fact")  # user_fact / preference / decision / tool_result
    importance: Mapped[float] = mapped_column(Float, default=0.5)      # 重要性评分（用于衰减和检索优先级）
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    ttl_days: Mapped[int] = mapped_column(Integer, nullable=True)      # 过期天数（到期自动清理）
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class KnowledgeMemory(Base, UUIDMixin, TimestampMixin):
    """知识记忆 — 结构化的持久知识（支持版本管理）"""
    __tablename__ = "knowledge_memories"

    namespace: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # 命名空间（如部门、项目）
    key: Mapped[str] = mapped_column(String(128), nullable=False)                    # 唯一键
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), default="text")
    embedding: Mapped[list] = mapped_column(JSON, nullable=True)
    meta: Mapped[dict] = mapped_column("meta", JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)                         # 版本号（写入时递增）
