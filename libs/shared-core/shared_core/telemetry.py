import os


def setup_telemetry(service_name: str | None = None) -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    except ImportError:
        return

    name = service_name or os.getenv("OTEL_SERVICE_NAME", "unknown-service")

    # gRPC OTLP exporter expects host:port (strip URL scheme if present)
    for prefix in ("https://", "http://"):
        if endpoint.startswith(prefix):
            endpoint = endpoint[len(prefix):]
            break

    resource = Resource.create({
        "service.name": name,
        "service.namespace": "smart-attendance"
    })

    provider = TracerProvider(resource=resource)

    # No TLS between pods so insecure
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    HTTPXClientInstrumentor().instrument()


def instrument_app(app) -> None:
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip():
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        pass