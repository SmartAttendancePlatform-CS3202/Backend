import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor


# function that specify which endpoints present traces
# function specify which labels to find trace services
# function that create traceing
def setup_telemetry(service_name: str | None = None) -> None:
    name = service_name or os.getenv("OTEL_SERVICE_NAME", "unknown-service")
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()

    if not endpoint:
        return

    resource = Resource.create({
        "service.name": name,
        "service.namespace": "smart-attendance"
    })

    provider= TracerProvidor(resource=resource)

    #No TLS between pods so insecure
    exporter= OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(Batch_span_processor(exporter))
    trace.set_tracer_provider(provider)

    HTTPXClientInstrumentor().instrument()

def instrument_app(app)-> None:
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip():
        return
    
    FastAPIInstrumentor.instrument_app(app)