"""成本控制模块：token 用量计算、预算检查、费用估算"""
from typing import Dict, Optional, Any
from datetime import datetime, timezone, date
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.token_usage import TokenUsageRecord, TokenBudget


# 各模型定价（美元 / 百万 token）
MODEL_PRICING: Dict[str, Dict[str, Dict[str, float]]] = {
    "openai": {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4.1": {"input": 2.00, "output": 8.00},
        "gpt-4.1-mini": {"input": 0.10, "output": 0.40},
    },
    "deepseek": {
        "deepseek-chat": {"input": 0.27, "output": 1.10},
        "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    },
    "qwen": {
        "qwen-max": {"input": 0.40, "output": 1.20},
        "qwen-plus": {"input": 0.20, "output": 0.80},
        "qwen-turbo": {"input": 0.08, "output": 0.20},
    },
    "zhipu": {
        "glm-4-plus": {"input": 0.70, "output": 0.70},
        "glm-4-flash": {"input": 0.01, "output": 0.01},
    },
    "ollama": {
        "qwen2.5:7b": {"input": 0.00, "output": 0.00},
    },
}


@dataclass
class BudgetStatus:
    """预算检查结果"""
    within_budget: bool = True
    daily_usage: int = 0
    daily_limit: int = 100000
    monthly_cost: float = 0.0
    monthly_limit: float = 30.0
    warning: Optional[str] = None


class CostCalculator:
    """费用估算器：根据 token 用量和模型定价计算费用"""

    @staticmethod
    def estimate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = MODEL_PRICING.get(provider, {}).get(model, {"input": 0.0, "output": 0.0})
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)


class BudgetController:
    """预算控制器：检查用户预算限额并记录用量"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_budget(self, user_id: str) -> BudgetStatus:
        """检查用户是否超出预算"""
        result = await self.db.execute(
            select(TokenBudget).where(TokenBudget.user_id == user_id)
        )
        budget = result.scalar_one_or_none()
        if not budget:
            return BudgetStatus()

        today = datetime.now(timezone.utc).date()
        daily_usage = await self._get_daily_usage(user_id, today)
        monthly_usage = await self._get_monthly_cost(user_id, today)

        status = BudgetStatus(
            daily_limit=budget.daily_limit,
            monthly_limit=budget.monthly_cost_limit,
            daily_usage=daily_usage,
            monthly_cost=monthly_usage,
        )

        if daily_usage >= budget.daily_limit:
            status.within_budget = False
            status.warning = f"今日 Token 用量已达上限（{daily_usage}/{budget.daily_limit}）"

        if monthly_usage >= budget.monthly_cost_limit:
            status.within_budget = False
            status.warning = f"月度费用已达上限（${monthly_usage:.2f}/${budget.monthly_cost_limit:.2f}）"

        usage_ratio = daily_usage / budget.daily_limit if budget.daily_limit > 0 else 0
        if usage_ratio >= budget.warning_threshold and usage_ratio < 1.0:
            status.warning = f"今日用量已达 {usage_ratio:.0%}（{daily_usage}/{budget.daily_limit}）"

        return status

    async def record_usage(self, record: TokenUsageRecord):
        """记录一次 token 用量"""
        self.db.add(record)

    async def _get_daily_usage(self, user_id: str, day: date) -> int:
        """查询用户指定日期的总 token 用量"""
        result = await self.db.execute(
            select(func.coalesce(func.sum(TokenUsageRecord.total_tokens), 0))
            .where(
                TokenUsageRecord.user_id == user_id,
                func.date(TokenUsageRecord.created_at) == day,
            )
        )
        return result.scalar() or 0

    async def _get_monthly_cost(self, user_id: str, day: date) -> float:
        """查询用户当月的总费用"""
        first_day = day.replace(day=1)
        result = await self.db.execute(
            select(func.coalesce(func.sum(TokenUsageRecord.estimated_cost), 0.0))
            .where(
                TokenUsageRecord.user_id == user_id,
                func.date(TokenUsageRecord.created_at) >= first_day,
            )
        )
        return result.scalar() or 0.0
