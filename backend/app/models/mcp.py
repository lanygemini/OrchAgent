from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, JSON, Boolean
from app.db.base import Base, UUIDMixin, TimestampMixin


class MCPServer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "mcp_servers"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    transport: Mapped[str] = mapped_column(String(16), nullable=False)
    command: Mapped[str] = mapped_column(String(256), nullable=True)
    args: Mapped[list] = mapped_column(JSON, default=list)
    env: Mapped[dict] = mapped_column(JSON, default=dict)
    url: Mapped[str] = mapped_column(String(512), nullable=True)
    headers: Mapped[dict] = mapped_column(JSON, default=dict)
    auth_type: Mapped[str] = mapped_column(String(16), default="none")
    auth_config: Mapped[dict] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
