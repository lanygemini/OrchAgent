"""分布式追踪：基于 OpenTelemetry 的链路追踪（可选）"""
from typing import Optional

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False


def setup_tracing(service_name: str = "orchagent", otlp_endpoint: Optional[str] = None):
    """初始化 OpenTelemetry 追踪（需安装 opentelemetry 相关包）"""
    if not OPENTELEMETRY_AVAILABLE:
        return

    provider = TracerProvider()
    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)


def get_tracer():
    if OPENTELEMETRY_AVAILABLE:
        return trace.get_tracer(__name__)
    return None
