from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, JSON, Float, ForeignKey
from app.db.base import Base, UUIDMixin, TimestampMixin
from typing import List


class Workflow(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workflows"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")

    start_node_id: Mapped[str] = mapped_column(String(36), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    nodes: Mapped[List["WorkflowNode"]] = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan", lazy="selectin")
    edges: Mapped[List["WorkflowEdge"]] = relationship("WorkflowEdge", back_populates="workflow", cascade="all, delete-orphan", lazy="selectin")


class WorkflowNode(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workflow_nodes"

    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str] = mapped_column(String(128), default="")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    position_x: Mapped[float] = mapped_column(Float, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, default=0.0)
    agent_id: Mapped[str] = mapped_column(String(36), nullable=True)
    tool_id: Mapped[str] = mapped_column(String(36), nullable=True)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="nodes")


class WorkflowEdge(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workflow_edges"

    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(36), nullable=False)
    condition_expr: Mapped[str] = mapped_column(String(512), nullable=True)
    label: Mapped[str] = mapped_column(String(64), default="")

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="edges")
