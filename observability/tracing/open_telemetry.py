from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.trace import Status, StatusCode
import os
import functools
import time
import logging

logger = logging.getLogger(__name__)

def init_tracing(app=None, service_name: str = "llm-gateway"):
    """Initialize OpenTelemetry with OTLP exporter."""
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    
    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        "deployment.environment": os.environ.get("ENVIRONMENT", "development")
    })
    
    provider = TracerProvider(resource=resource)
    try:
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
    except Exception as e:
        logger.warning(f"Failed to initialize OTLP exporter: {e}")
    
    # Instrument libraries
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    
    if app:
        FastAPIInstrumentor.instrument_app(app)
    
    logger.info(f"OpenTelemetry initialized with OTLP endpoint: {otlp_endpoint}")
    return provider

def trace_span(name: str, attributes: dict = None):
    """Decorator to create a span around an async function."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(name) as span:
                if attributes:
                    span.set_attributes(attributes)
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        return wrapper
    return decorator

# Keep original @trace stub for backward compatibility, now using real spans
def trace(func):
    return trace_span(func.__name__)(func)
