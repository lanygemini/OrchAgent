"""统计 API：获取仪表盘汇总数据"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta

from app.dependencies import get_db, get_current_user
from app.models.agent import Agent
from app.models.workflow import Workflow
from app.models.tool import Tool
from app.models.execution import WorkflowExecution
from app.models.token_usage import TokenUsageRecord
from app.schemas.stats import DashboardStats

router = APIRouter(prefix="/api/v1/stats", tags=["统计"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """获取当前用户的仪表盘数据（Agent/工作流/工具/执行次数统计）"""
    agent_count = await db.scalar(select(func.count(Agent.id)).where(Agent.owner_id == user.sub))
    workflow_count = await db.scalar(select(func.count(Workflow.id)).where(Workflow.owner_id == user.sub))
    tool_count = await db.scalar(select(func.count(Tool.id)).where(Tool.owner_id == user.sub))

    exec_count = await db.scalar(
        select(func.count(WorkflowExecution.id)).where(WorkflowExecution.created_by == user.sub)
    )

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    exec_today = await db.scalar(
        select(func.count(WorkflowExecution.id))
        .where(WorkflowExecution.created_by == user.sub, WorkflowExecution.created_at >= today_start)
    )

    active_execs = await db.scalar(
        select(func.count(WorkflowExecution.id))
        .where(WorkflowExecution.created_by == user.sub, WorkflowExecution.status.in_(["pending", "running"]))
    )

    # Token 用量统计
    token_agg = await db.execute(
        select(
            func.coalesce(func.sum(TokenUsageRecord.total_tokens), 0),
            func.coalesce(func.sum(TokenUsageRecord.estimated_cost), 0.0),
        ).where(TokenUsageRecord.user_id == user.sub)
    )
    total_tokens, total_cost = token_agg.one()

    # 成功率
    completed_count = await db.scalar(
        select(func.count(WorkflowExecution.id))
        .where(WorkflowExecution.created_by == user.sub, WorkflowExecution.status == "completed")
    )
    finished_count = await db.scalar(
        select(func.count(WorkflowExecution.id))
        .where(WorkflowExecution.created_by == user.sub, WorkflowExecution.status.in_(["completed", "failed", "cancelled"]))
    )
    success_rate = round((completed_count or 0) / finished_count, 4) if finished_count else 0.0

    # 最近 5 条执行记录
    recent_result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.created_by == user.sub)
        .order_by(WorkflowExecution.created_at.desc())
        .limit(5)
    )
    recent_execs = recent_result.scalars().all()
    recent_executions = [
        {
            "id": e.id,
            "workflow_id": e.workflow_id,
            "workflow_name": e.workflow_name,
            "status": e.status,
            "input_data": e.input_data,
            "output_data": e.output_data,
            "token_usage": e.token_usage,
            "step_count": 0,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "error_message": e.error_message,
        }
        for e in recent_execs
    ]

    return DashboardStats(
        total_agents=agent_count or 0,
        total_workflows=workflow_count or 0,
        total_tools=tool_count or 0,
        total_executions=exec_count or 0,
        total_tokens=total_tokens,
        total_cost=round(total_cost, 6),
        success_rate=success_rate,
        executions_today=exec_today or 0,
        active_executions=active_execs or 0,
        recent_executions=recent_executions,
    )
