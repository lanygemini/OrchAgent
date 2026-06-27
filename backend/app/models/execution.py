"""执行记录模型：工作流执行实例和每一步的详细日志"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, JSON, DateTime
from app.db.base import Base, UUIDMixin, TimestampMixin
from datetime import datetime


class WorkflowExecution(Base, UUIDMixin, TimestampMixin):
    """工作流执行记录 — 记录一次完整的执行过程"""
    __tablename__ = "workflow_executions"

    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workflow_name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending / running / paused / completed / failed / cancelled
    state_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)   # 中间状态快照（用于恢复）
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    output_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    token_usage: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)


class ExecutionStep(Base, UUIDMixin):
    """执行步骤日志 — 工作流中每个节点的执行明细"""
    __tablename__ = "execution_steps"

    execution_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(36), nullable=False)
    node_label: Mapped[str] = mapped_column(String(128), default="")
    step_type: Mapped[str] = mapped_column(String(16), nullable=False)  # agent / tool / condition / human
    input_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    output_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    token_usage: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
