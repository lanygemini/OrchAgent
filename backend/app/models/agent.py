"""Agent 模型：存储 AI Agent 的配置信息"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, Integer, Boolean
from app.db.base import Base, UUIDMixin, TimestampMixin


class Agent(Base, UUIDMixin, TimestampMixin):
    """AI Agent — 包含角色设定、LLM 配置、记忆策略等"""
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(128), default="助手")
    description: Mapped[str] = mapped_column(Text, default="")

    # LLM 配置
    llm_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    system_prompt: Mapped[str] = mapped_column(Text, default="")

    # 记忆配置
    enable_memory: Mapped[bool] = mapped_column(Boolean, default=True)
    memory_window: Mapped[int] = mapped_column(Integer, default=10)
    memory_policy: Mapped[str] = mapped_column(String(16), default="private")

    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
