"""工作流模型：DAG 定义 —— 包含节点列表和边列表"""
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, JSON, Float, ForeignKey
from app.db.base import Base, UUIDMixin, TimestampMixin
from typing import List


class Workflow(Base, UUIDMixin, TimestampMixin):
    """工作流定义 — 一个 DAG 图结构"""
    __tablename__ = "workflows"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft / published / archived

    start_node_id: Mapped[str] = mapped_column(String(36), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    nodes: Mapped[List["WorkflowNode"]] = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan", lazy="selectin")
    edges: Mapped[List["WorkflowEdge"]] = relationship("WorkflowEdge", back_populates="workflow", cascade="all, delete-orphan", lazy="selectin")


class WorkflowNode(Base, UUIDMixin, TimestampMixin):
    """工作流节点 — 可以是 agent / tool / condition / start / end / fork / join / human 等类型"""
    __tablename__ = "workflow_nodes"

    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str] = mapped_column(String(128), default="")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    position_x: Mapped[float] = mapped_column(Float, default=0.0)  # 前端画布 X 坐标
    position_y: Mapped[float] = mapped_column(Float, default=0.0)  # 前端画布 Y 坐标
    agent_id: Mapped[str] = mapped_column(String(36), nullable=True)    # 关联的 Agent ID（type=agent 时）
    tool_id: Mapped[str] = mapped_column(String(36), nullable=True)     # 关联的 Tool ID（type=tool 时）

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="nodes")


class WorkflowEdge(Base, UUIDMixin, TimestampMixin):
    """工作流边 — 连接两个节点的有向边，可带条件表达式"""
    __tablename__ = "workflow_edges"

    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(36), nullable=False)
    condition_expr: Mapped[str] = mapped_column(String(512), nullable=True)  # 条件分支表达式
    label: Mapped[str] = mapped_column(String(64), default="")

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="edges")
