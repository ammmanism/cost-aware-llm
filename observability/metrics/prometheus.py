from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "llm_gateway_requests_total",
    "Total LLM requests",
    ["provider", "model", "status"]
)

LATENCY = Histogram(
    "llm_gateway_latency_seconds",
    "LLM request latency",
    ["provider", "model"]
)

CACHE_HIT = Counter(
    "llm_gateway_cache_hits_total",
    "Total cache hits",
    ["type"]
)
