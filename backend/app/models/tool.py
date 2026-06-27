from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, JSON, Boolean
from app.db.base import Base, UUIDMixin, TimestampMixin


class Tool(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tools"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    tool_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(16), default="builtin")
    source_id: Mapped[str] = mapped_column(String(36), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
