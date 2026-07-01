# OrchAgent — Token 成本控制与管理设计

---

## 一、成本模型

### 各模型价格（2026 年参考，美元/1M tokens）

```python
MODEL_PRICING = {
    "openai": {
        "gpt-4o":           {"input": 2.50,  "output": 10.00},
        "gpt-4o-mini":      {"input": 0.15,  "output": 0.60},
        "gpt-4.1":          {"input": 2.00,  "output": 8.00},
        "gpt-4.1-mini":     {"input": 0.10,  "output": 0.40},
    },
    "deepseek": {
        "deepseek-chat":    {"input": 0.27,  "output": 1.10},
        "deepseek-reasoner":{"input": 0.55,  "output": 2.19},
    },
    "qwen": {
        "qwen-max":         {"input": 0.40,  "output": 1.20},
        "qwen-plus":        {"input": 0.20,  "output": 0.80},
        "qwen-turbo":       {"input": 0.08,  "output": 0.20},
    },
    "zhipu": {
        "glm-4-plus":       {"input": 0.70,  "output": 0.70},
        "glm-4-flash":      {"input": 0.01,  "output": 0.01},
    },
    "ollama": {
        "qwen2.5:7b":       {"input": 0.00,  "output": 0.00},
    },
}
```

---

## 二、Token 使用追踪

```python
class TokenUsageRecord(Base):
    __tablename__ = "token_usage_records"

    id: str
    user_id: str
    agent_id: str
    execution_id: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    call_type: str
    success: bool = True
    error_code: str
    created_at: datetime

class TokenBudget(Base):
    __tablename__ = "token_budgets"

    id: str
    user_id: str
    daily_limit: int = 100_000
    weekly_limit: int = 500_000
    monthly_limit: int = 2_000_000
    daily_cost_limit: float = 1.0
    monthly_cost_limit: float = 30.0
    warning_threshold: float = 0.8
```

---

## 三、预算控制系统

```python
class BudgetController:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis

    async def check_and_reserve(self, user_id: str, estimated_tokens: int) -> bool:
        budget = await self._get_user_budget(user_id)
        if not budget:
            return True

        daily_used = await self._get_period_usage(user_id, "day")
        weekly_used = await self._get_period_usage(user_id, "week")
        monthly_used = await self._get_period_usage(user_id, "month")

        checks = [
            (daily_used + estimated_tokens, budget.daily_limit, "每日"),
            (weekly_used + estimated_tokens, budget.weekly_limit, "每周"),
            (monthly_used + estimated_tokens, budget.monthly_limit, "每月"),
        ]
        for used, limit, period_name in checks:
            if used > limit:
                raise BudgetExceededError(
                    f"{period_name} Token 预算已用完 ({used}/{limit})",
                    period=period_name, used=used, limit=limit,
                )
        return True
```

### 预算超限处理

```python
class BudgetAwareLLMFactory:
    async def create_with_budget(self, user_id: str, config: AgentConfig):
        try:
            estimated = self._estimate_call_tokens(config)
            await self.bc.check_and_reserve(user_id, estimated)
        except BudgetExceededError:
            if config.llm_provider != "ollama":
                return self._get_fallback_model(config)
            raise
        return self._create_llm(config)

    def _get_fallback_model(self, config: AgentConfig) -> ChatModel:
        fallback_map = {
            "gpt-4o": ChatOpenAI(model="gpt-4o-mini"),
            "gpt-4.1": ChatOpenAI(model="gpt-4.1-mini"),
            "deepseek-chat": ChatOpenAI(model="gpt-4o-mini"),
            "qwen-max": ChatTongyi(model="qwen-turbo"),
            "glm-4-plus": ChatZhipuAI(model="glm-4-flash"),
        }
        fallback = fallback_map.get(config.model_name)
        if not fallback:
            return ChatOllama(model="qwen2.5:7b")
        return fallback
```

---

## 四、省钱策略

| 策略 | 说明 | 节省程度 |
|------|------|---------|
| **L2 摘要用小模型** | 会话摘要用 gpt-4o-mini | 节省 90%+ |
| **L3 记忆提取用小模型** | 记忆提取用 gpt-4o-mini | 节省 90%+ |
| **简单路由先判断** | 普通问答走便宜模型，复杂任务走强模型 | 节省 40-70% |
| **Prompt 缓存**（OpenAI） | 相同的 System Prompt 只付费一次 | 节省 50% |
| **结果缓存** | 相同问题返回缓存结果 | 节省 100% |
| **按需降级** | 超预算自动降级到便宜模型 | 自动 |
| **本地模型兜底** | Ollama 跑 qwen2.5:7b | 完全免费 |

---

## 五、用量仪表盘 API

```
GET    /api/v1/stats/usage                 用量统计
GET    /api/v1/stats/budget                预算状态
GET    /api/v1/admin/usage/overview         平台总用量概览
GET    /api/v1/admin/usage/users            各用户用量排行榜
PUT    /api/v1/admin/usage/user/{id}/budget 设置用户预算
```
