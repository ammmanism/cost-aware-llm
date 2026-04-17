from prometheus_client import Counter, Gauge, Histogram
import time
import logging

logger = logging.getLogger(__name__)

# Cost-related metrics
cost_per_request = Histogram(
    'llm_gateway_cost_per_request_usd',
    'Cost per request in USD',
    ['tenant_id', 'model', 'provider'],
    buckets=[0.0001, 0.001, 0.01, 0.1, 1.0]
)

total_cost = Counter(
    'llm_gateway_total_cost_usd',
    'Total cost in USD',
    ['tenant_id', 'model', 'provider']
)

tenant_daily_cost = Gauge(
    'llm_gateway_tenant_daily_cost_usd',
    'Daily cost per tenant in USD',
    ['tenant_id']
)

cache_hit_ratio = Gauge(
    'llm_gateway_cache_hit_ratio',
    'Cache hit ratio (0-1)',
    ['cache_type']
)

active_streams = Gauge(
    'llm_gateway_active_streams',
    'Number of active streaming connections',
    ['tenant_id']
)

def record_cost(tenant_id: str, model: str, provider: str, cost_usd: float):
    """Record cost for a request."""
    try:
        cost_per_request.labels(tenant_id=tenant_id, model=model, provider=provider).observe(cost_usd)
        total_cost.labels(tenant_id=tenant_id, model=model, provider=provider).inc(cost_usd)
        
        # In a real system, daily cost would be reset at midnight or use Prometheus aggregation
        # Simplified manual update for demonstration
        tenant_daily_cost.labels(tenant_id=tenant_id).inc(cost_usd)
    except Exception as e:
        logger.error(f"Failed to record Prometheus cost metrics: {e}")

def record_cache_hit(cache_type: str, is_hit: bool):
    """Update cache hit ratio metrics."""
    # Logic to update ratio gauge
    pass

def update_active_streams(tenant_id: str, delta: int):
    """Update active streams count."""
    try:
        active_streams.labels(tenant_id=tenant_id).inc(delta)
    except Exception as e:
        logger.error(f"Failed to update active streams metric: {e}")
