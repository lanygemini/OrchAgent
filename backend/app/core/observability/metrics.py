from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from fastapi import Response

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

tool_calls_total = Counter(
    "orch_tool_calls_total",
    "Total tool calls",
    ["tool_type", "status"],
)

workflow_executions_total = Counter(
    "orch_workflow_executions_total",
    "Total workflow executions",
    ["status"],
)

memory_retrieval_latency = Histogram(
    "orch_memory_retrieval_latency_seconds",
    "Memory retrieval latency",
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0),
)

active_executions = Gauge(
    "orch_active_executions",
    "Currently active workflow executions",
)

api_requests_total = Counter(
    "orch_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)


async def metrics_endpoint():
    return Response(content=generate_latest(REGISTRY), media_type="text/plain")
