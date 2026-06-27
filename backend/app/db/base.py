"""SQLAlchemy ORM 基类与通用 Mixin"""
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, func, Text, Float, Boolean, Integer, Enum as SAEnum, JSON
import uuid
from datetime import datetime


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """为模型自动添加 created_at / updated_at 时间戳"""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UUIDMixin:
    """为模型使用 UUID 字符串作为主键"""
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
