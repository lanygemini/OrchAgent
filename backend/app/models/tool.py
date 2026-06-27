"""工具模型：注册 Agent 可调用的工具（内置、自定义、MCP 来源）"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, JSON, Boolean
from app.db.base import Base, UUIDMixin, TimestampMixin


class Tool(Base, UUIDMixin, TimestampMixin):
    """注册的工具 — 描述调用方式、参数 schema 和来源"""
    __tablename__ = "tools"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # builtin / custom / mcp
    tool_schema: Mapped[dict] = mapped_column(JSON, default=dict)   # 参数定义（JSON Schema）
    config: Mapped[dict] = mapped_column(JSON, default=dict)        # 运行时配置
    source: Mapped[str] = mapped_column(String(16), default="builtin")
    source_id: Mapped[str] = mapped_column(String(36), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
