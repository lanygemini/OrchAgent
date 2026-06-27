import asyncio
import random
import time
from enum import Enum
from typing import Optional, Callable, Any, Awaitable, TypeVar, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

T = TypeVar("T")


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


class ErrorSeverity(str, Enum):
    RETRYABLE = "retryable"
    DEGRADABLE = "degradable"
    NEEDS_HUMAN = "needs_human"
    FATAL = "fatal"


ERROR_SEVERITY_MAP: Dict[ErrorCode, ErrorSeverity] = {
    ErrorCode.LLM_TIMEOUT: ErrorSeverity.RETRYABLE,
    ErrorCode.LLM_RATE_LIMITED: ErrorSeverity.RETRYABLE,
    ErrorCode.LLM_NETWORK: ErrorSeverity.RETRYABLE,
    ErrorCode.TOOL_TIMEOUT: ErrorSeverity.RETRYABLE,
    ErrorCode.MCP_CONNECTION_LOST: ErrorSeverity.RETRYABLE,
    ErrorCode.TOOL_EXECUTION_FAILED: ErrorSeverity.DEGRADABLE,
    ErrorCode.MCP_SERVER_INTERNAL: ErrorSeverity.DEGRADABLE,
    ErrorCode.LLM_HALLUCINATED_TOOL: ErrorSeverity.DEGRADABLE,
    ErrorCode.WF_TIMEOUT: ErrorSeverity.FATAL,
    ErrorCode.LLM_UNAUTHORIZED: ErrorSeverity.FATAL,
    ErrorCode.SYS_INTERNAL: ErrorSeverity.FATAL,
}


class OrchAgentError(Exception):
    def __init__(self, code: ErrorCode, message: str, severity: Optional[ErrorSeverity] = None):
        self.code = code
        self.severity = severity or ERROR_SEVERITY_MAP.get(code, ErrorSeverity.FATAL)
        super().__init__(f"[{code.value}] {message}")


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


class RetryHandler:
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    async def execute_with_retry(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        last_error: Optional[Exception] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except OrchAgentError as e:
                if e.severity != ErrorSeverity.RETRYABLE:
                    raise
                last_error = e
            except Exception as e:
                last_error = e

            if attempt < self.config.max_retries:
                delay = self._get_delay(attempt)
                await asyncio.sleep(delay)

        raise last_error or OrchAgentError(ErrorCode.SYS_INTERNAL, "超过最大重试次数")

    def _get_delay(self, attempt: int) -> float:
        delay = min(
            self.config.base_delay * (self.config.backoff_multiplier ** attempt),
            self.config.max_delay,
        )
        if self.config.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0, half_open_max_calls: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0

    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time and (datetime.now() - self.last_failure_time) > timedelta(seconds=self.recovery_timeout):
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
            else:
                raise OrchAgentError(ErrorCode.SYS_INTERNAL, "熔断器已打开，请求被拒绝")

        if self.state == CircuitBreakerState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise OrchAgentError(ErrorCode.SYS_INTERNAL, "熔断器半开状态达到上限")
            self.half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            if self.state in (CircuitBreakerState.HALF_OPEN, CircuitBreakerState.CLOSED):
                self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class FallbackManager:
    def __init__(self, fallback_providers: Dict[str, str]):
        self.fallback_providers = fallback_providers

    def get_fallback(self, primary_provider: str) -> Optional[str]:
        return self.fallback_providers.get(primary_provider)
