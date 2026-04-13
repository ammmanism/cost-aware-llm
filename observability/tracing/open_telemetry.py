from opentelemetry import trace

tracer = trace.get_tracer("llm-gateway")

def start_span(name: str):
    return tracer.start_as_current_span(name)
