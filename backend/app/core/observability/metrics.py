"""Prometheus 指标定义：LLM 调用、工具调用、工作流执行、API 请求等"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from fastapi import Response

# LLM 相关指标
llm_requests_total = Counter(
    "orch_llm_requests_total",
    "Total LLM requests",
    ["provider", "model", "status"],
)

llm_latency_seconds = Histogram(
    "orch_llm_latency_seconds",
    "LLM call latency in seconds",
    ["provider"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

llm_tokens_total = Counter(
    "orch_llm_tokens_total",
    "Total LLM tokens consumed",
    ["provider", "token_type"],
)

# 工具调用指标
tool_calls_total = Counter(
    "orch_tool_calls_total",
    "Total tool calls",
    ["tool_type", "status"],
)

# 工作流执行指标
workflow_executions_total = Counter(
    "orch_workflow_executions_total",
    "Total workflow executions",
    ["status"],
)

# 记忆检索指标
memory_retrieval_latency = Histogram(
    "orch_memory_retrieval_latency_seconds",
    "Memory retrieval latency",
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0),
)

# 活跃执行数
active_executions = Gauge(
    "orch_active_executions",
    "Currently active workflow executions",
)

# API 请求指标
api_requests_total = Counter(
    "orch_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)


async def metrics_endpoint():
    """Prometheus 指标暴露端点"""
    return Response(content=generate_latest(REGISTRY), media_type="text/plain")
