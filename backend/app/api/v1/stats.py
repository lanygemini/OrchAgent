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

    return DashboardStats(
        total_agents=agent_count or 0,
        total_workflows=workflow_count or 0,
        total_tools=tool_count or 0,
        total_executions=exec_count or 0,
        executions_today=exec_today or 0,
        active_executions=active_execs or 0,
    )
