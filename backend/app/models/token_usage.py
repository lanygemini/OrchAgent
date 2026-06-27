from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Boolean, DateTime
from app.db.base import Base, UUIDMixin, TimestampMixin
from datetime import datetime


class TokenUsageRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "token_usage_records"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    execution_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    call_type: Mapped[str] = mapped_column(String(16), default="llm")
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_code: Mapped[str] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class TokenBudget(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "token_budgets"

    user_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    daily_limit: Mapped[int] = mapped_column(Integer, default=100000)
    weekly_limit: Mapped[int] = mapped_column(Integer, default=500000)
    monthly_limit: Mapped[int] = mapped_column(Integer, default=2000000)
    daily_cost_limit: Mapped[float] = mapped_column(Float, default=1.0)
    monthly_cost_limit: Mapped[float] = mapped_column(Float, default=30.0)
    warning_threshold: Mapped[float] = mapped_column(Float, default=0.8)
