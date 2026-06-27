# OrchAgent — 错误处理与重试策略设计

---

## 一、错误分类体系

### 错误码体系

```python
class ErrorCode(str, Enum):
    LLM_TIMEOUT = "E_LLM_TIMEOUT"
    LLM_RATE_LIMITED = "E_LLM_RATE_LIMITED"
    LLM_TOKEN_OVERFLOW = "E_LLM_TOKEN_OVERFLOW"
    LLM_NETWORK = "E_LLM_NETWORK"
    LLM_UNAUTHORIZED = "E_LLM_UNAUTHORIZED"
    LLM_INVALID_RESPONSE = "E_LLM_INVALID_RESPONSE"
    LLM_HALLUCINATED_TOOL = "E_LLM_HALLUCINATED_TOOL"
    TOOL_TIMEOUT = "E_TOOL_TIMEOUT"
    TOOL_EXECUTION_FAILED = "E_TOOL_EXECUTION_FAILED"
    TOOL_NOT_FOUND = "E_TOOL_NOT_FOUND"
    TOOL_SANDBOX_VIOLATION = "E_TOOL_SANDBOX_VIOLATION"
    MCP_CONNECTION_LOST = "E_MCP_CONNECTION_LOST"
    MCP_SERVER_INTERNAL = "E_MCP_SERVER_INTERNAL"
    WF_TIMEOUT = "E_WF_TIMEOUT"
    WF_CYCLE_DETECTED = "E_WF_CYCLE_DETECTED"
    MEM_RETRIEVAL_FAILED = "E_MEM_RETRIEVAL_FAILED"
    MEM_EXTRACTION_FAILED = "E_MEM_EXTRACTION_FAILED"
    SYS_DB_ERROR = "E_SYS_DB_ERROR"
    SYS_REDIS_ERROR = "E_SYS_REDIS_ERROR"
    SYS_INTERNAL = "E_SYS_INTERNAL"
```

### 错误分级

```python
class ErrorSeverity(Enum):
    RETRYABLE = "retryable"
    DEGRADABLE = "degradable"
    NEEDS_HUMAN = "needs_human"
    FATAL = "fatal"

ERROR_SEVERITY_MAP = {
    ErrorCode.LLM_TIMEOUT:         ErrorSeverity.RETRYABLE,
    ErrorCode.LLM_RATE_LIMITED:    ErrorSeverity.RETRYABLE,
    ErrorCode.LLM_NETWORK:         ErrorSeverity.RETRYABLE,
    ErrorCode.TOOL_TIMEOUT:        ErrorSeverity.RETRYABLE,
    ErrorCode.MCP_CONNECTION_LOST: ErrorSeverity.RETRYABLE,
    ErrorCode.TOOL_EXECUTION_FAILED: ErrorSeverity.DEGRADABLE,
    ErrorCode.MCP_SERVER_INTERNAL: ErrorSeverity.DEGRADABLE,
    ErrorCode.LLM_HALLUCINATED_TOOL: ErrorSeverity.DEGRADABLE,
    ErrorCode.WF_TIMEOUT:          ErrorSeverity.FATAL,
    ErrorCode.LLM_UNAUTHORIZED:    ErrorSeverity.FATAL,
    ErrorCode.SYS_INTERNAL:        ErrorSeverity.FATAL,
}
```

---

## 二、重试策略

### 指数退避 + 抖动

```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True

class RetryHandler:
    def __init__(self, config: RetryConfig):
        self.config = config

    async def execute_with_retry(self, func, *args, **kwargs):
        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except AgentError as e:
                last_error = e
                if attempt >= self.config.max_retries:
                    raise MaxRetriesExceededError(
                        f"重试 {self.config.max_retries} 次后仍失败",
                        original_error=e,
                    )
                if not self._should_retry(e.error_code):
                    raise
                delay = self._calc_backoff(attempt)
                await asyncio.sleep(delay)
        raise last_error

    def _calc_backoff(self, attempt: int) -> float:
        delay = self.config.base_delay * (self.config.backoff_multiplier ** attempt)
        delay = min(delay, self.config.max_delay)
        if self.config.jitter:
            delay = delay * (0.5 + random.random())
        return delay
```

---

## 三、超时控制

```python
@dataclass
class TimeoutConfig:
    llm_request_timeout: float = 30.0
    llm_stream_timeout: float = 120.0
    llm_first_token_timeout: float = 10.0
    tool_execution_timeout: float = 15.0
    mcp_connect_timeout: float = 10.0
    mcp_request_timeout: float = 30.0
    workflow_total_timeout: float = 300.0
    node_execution_timeout: float = 60.0
    memory_extraction_timeout: float = 30.0
    memory_retrieval_timeout: float = 5.0
```

---

## 四、熔断器

```python
class CircuitBreaker:
    def __init__(self, redis: Redis, failure_threshold: int = 5,
                 recovery_timeout: int = 60, half_open_max_requests: int = 3):
        self.redis = redis
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests

    async def is_open(self, resource: str) -> bool:
        state = await self.redis.get(f"cb:state:{resource}")
        return state == b"open"

    async def open(self, resource: str, duration: int = None):
        ttl = duration or self.recovery_timeout
        await self.redis.setex(f"cb:state:{resource}", ttl, "open")

    async def close(self, resource: str):
        await self.redis.delete(f"cb:state:{resource}")
        await self.redis.delete(f"cb:failure_count:{resource}")

    async def record_failure(self, resource: str):
        count = await self.redis.incr(f"cb:failure_count:{resource}")
        if count >= self.failure_threshold:
            await self.open(resource)

    async def record_success(self, resource: str):
        await self.redis.delete(f"cb:failure_count:{resource}")
```

---

## 五、降级策略

```python
class DegradationStrategy:
    async def degrade_llm(self, primary_model: str, error: AgentError) -> str:
        fallback_models = {
            "gpt-4o": "gpt-4o-mini",
            "deepseek-chat": "qwen-max",
            "qwen-max": "gpt-4o-mini",
        }
        fallback = fallback_models.get(primary_model)
        if fallback:
            return fallback
        return "ollama:qwen2.5:7b"

    async def degrade_tool(self, tool_name: str, node_config: dict, error: AgentError):
        skip_on_failure = node_config.get("skip_on_failure", False)
        if skip_on_failure:
            return node_config.get("fallback_value", "")
        return None
```

---

## 六、用户可见的错误提示

```python
class UserFacingError:
    USER_FRIENDLY_MESSAGES = {
        ErrorCode.LLM_TIMEOUT: "AI 服务响应较慢，请稍后重试",
        ErrorCode.LLM_RATE_LIMITED: "AI 服务繁忙，正在排队等待",
        ErrorCode.LLM_TOKEN_OVERFLOW: "输入内容过多，请精简后重试",
        ErrorCode.TOOL_TIMEOUT: "工具执行超时，已自动重试",
        ErrorCode.TOOL_EXECUTION_FAILED: "某个工具执行失败，已跳过继续执行",
        ErrorCode.MCP_CONNECTION_LOST: "外部服务连接中断，已自动重连",
        ErrorCode.WF_TIMEOUT: "工作流执行超时，已保存进度，可稍后恢复",
        ErrorCode.WF_CYCLE_DETECTED: "工作流存在循环依赖，请检查节点连接",
        ErrorCode.LLM_HALLUCINATED_TOOL: "AI 响应异常，已自动重试",
    }
```

---

## 七、配置总结

| 故障类型 | 重试次数 | 退避策略 | 超时 | 降级方案 |
|---------|---------|---------|------|---------|
| LLM 超时 | 3 | 指数 2s->4s->8s | 30s | 切换备用模型 |
| LLM 429限流 | 3 | 指数 10s->20s->40s | - | 切换备用模型 / 熔断 120s |
| 工具执行失败 | 1 | 固定 1s | 15s | 跳过节点 / 返回默认值 |
| MCP 连接断开 | 2 | 指数 1s->2s->4s | 10s | 跳过该工具 |
| 数据库异常 | 2 | 指数 0.5s->1s->2s | 5s | - |
| 工作流超时 | 0 | - | 300s | 保存Checkpoint，通知用户 |
| Token溢出 | 0 | - | - | 自动裁剪历史消息 |
