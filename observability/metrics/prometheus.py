from fastapi import Response
from prometheus_client import REGISTRY, Counter, Histogram, generate_latest

request_counter = Counter("llm_gateway_requests_total", "Total requests")
failure_counter = Counter("llm_gateway_failures_total", "Total failures")
latency_histogram = Histogram(
    "llm_gateway_request_duration_ms",
    "Request latency in ms",
    buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000],
)


def metrics_endpoint() -> Response:
    return Response(content=generate_latest(REGISTRY), media_type="text/plain")
