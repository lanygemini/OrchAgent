"""Token 用量与预算模型：记录 LLM 调用费用并控制预算"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Boolean, DateTime
from app.db.base import Base, UUIDMixin, TimestampMixin
from datetime import datetime


class TokenUsageRecord(Base, UUIDMixin, TimestampMixin):
    """Token 使用记录 — 每次 LLM 调用的 token 消耗和费用估算"""
    __tablename__ = "token_usage_records"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    execution_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)  # 美元计
    call_type: Mapped[str] = mapped_column(String(16), default="llm")
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_code: Mapped[str] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class TokenBudget(Base, UUIDMixin, TimestampMixin):
    """Token 预算 — 用户的每日 / 每周 / 每月用量限制"""
    __tablename__ = "token_budgets"

    user_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    daily_limit: Mapped[int] = mapped_column(Integer, default=100000)          # 每日 token 上限
    weekly_limit: Mapped[int] = mapped_column(Integer, default=500000)
    monthly_limit: Mapped[int] = mapped_column(Integer, default=2000000)
    daily_cost_limit: Mapped[float] = mapped_column(Float, default=1.0)       # 每日费用上限（美元）
    monthly_cost_limit: Mapped[float] = mapped_column(Float, default=30.0)
    warning_threshold: Mapped[float] = mapped_column(Float, default=0.8)      # 用量达到 80% 时告警
