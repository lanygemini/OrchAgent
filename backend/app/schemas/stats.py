"""统计面板 Schema"""
from typing import List, Dict, Any
from pydantic import BaseModel


class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    total_agents: int = 0
    total_workflows: int = 0
    total_tools: int = 0
    total_executions: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    success_rate: float = 0.0
    executions_today: int = 0
    active_executions: int = 0
    recent_executions: List[Dict[str, Any]] = []
