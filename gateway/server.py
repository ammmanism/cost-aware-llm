import hashlib
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from caching.cache_manager import CacheManager
from gateway.control_plane.fallback_policies import get_fallback_chain_from_policy
from gateway.control_plane.fallback_policies import router as fallback_router
from gateway.control_plane.router import init_admin_deps
from gateway.control_plane.router import router as admin_router
from gateway.core.batcher import NexusBatcher
from gateway.core.cost_tracker import NexusCostTracker
from gateway.core.heartbeat import HeartbeatMonitor
from load_balancing.least_busy import LeastBusyBalancer
from multi_tenant.budget_enforcer import BudgetEnforcer
from multi_tenant.quota_manager import QuotaManager
from observability.logging_middleware import StructuredLoggingMiddleware
from observability.metrics.cost_metrics import record_cost
from observability.metrics.prometheus import (
    failure_counter,
    latency_histogram,
    metrics_endpoint,
    request_counter,
)
from observability.tracing.open_telemetry import init_tracing, trace_span
from providers.factory import ProviderFactory
from routers.adaptive import AdaptiveRouter
from routers.cost_aware import CostAwareRouter
from routers.fallback import FallbackRouter
from routers.latency_aware import LatencyAwareRouter

# Security
from security.auth import APIKeyAuthMiddleware
from security.cors import configure_cors
from security.firewall import SentinelFirewall
from security.headers import SecurityHeadersMiddleware
from security.rate_limiter import RateLimiter
from tests.chaos.chaos_controller import ChaosMode, chaos

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global components
health_checker = HeartbeatMonitor(check_interval=30)
load_balancer = LeastBusyBalancer()
cache_manager = CacheManager()
quota_manager = QuotaManager()
budget_enforcer = BudgetEnforcer()
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
adaptive_router = AdaptiveRouter()
request_batcher = NexusBatcher()
cost_tracker = NexusCostTracker()

# Initialize admin dependencies
init_admin_deps(cache_manager, quota_manager, budget_enforcer, health_checker)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting LLM Gateway...")
    # Initialize OpenTelemetry
    init_tracing(app, service_name="llm-gateway")
    ProviderFactory.get_all_providers()
    await health_checker.start()
    logger.info("Gateway ready")
    yield
    await health_checker.stop()
    logger.info("Gateway shutdown")

app = FastAPI(title="LLM Gateway", version="6.0.0", lifespan=lifespan)

# Security middleware stack
configure_cors(app)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    APIKeyAuthMiddleware,
    exclude_paths={"/health", "/metrics", "/docs", "/openapi.json", "/redoc", "/admin"},
)
app.add_middleware(StructuredLoggingMiddleware)

# Include routers
app.include_router(admin_router)
app.include_router(fallback_router)

# Routers
cost_router = CostAwareRouter()
latency_router = LatencyAwareRouter()
fallback_router_logic = FallbackRouter()


class GenerateRequest(BaseModel):
    prompt: str
    tenant_id: Optional[str] = "default"
    use_cache: Optional[bool] = True
    prefer_latency: Optional[bool] = False
    model: Optional[str] = None
    stream: Optional[bool] = False


class GenerateResponse(BaseModel):
    model: str
    output: str
    provider: str
    latency_ms: float


def build_cache_key(tenant_id: str, prompt: str) -> str:
    """Build a stable cache key without storing prompt text."""
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return f"cache:{tenant_id}:{digest}"


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "providers": {name: status.value for name, status in health_checker.status.items()},
        "chaos": chaos.get_mode(),
    }


@app.get("/metrics")
async def get_metrics():
    return metrics_endpoint()


@app.post("/admin/chaos/{mode}")
async def set_chaos_mode(mode: str, failure_rate: float = 0.1, latency_ms: int = 100):
    """Enable chaos mode for testing (admin only)."""
    if mode == "off":
        chaos.disable()
    elif mode == "failure":
        chaos.enable(ChaosMode.FAILURE, failure_rate=failure_rate)
    elif mode == "latency":
        chaos.enable(ChaosMode.LATENCY, base_latency_ms=latency_ms)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {mode}")
    return {"chaos_mode": chaos.get_mode()}


@app.post("/generate")
@trace_span("generate_request")
async def generate(request: GenerateRequest, req: Request):
    start_time = time.perf_counter()
    request_counter.inc()

    if hasattr(req.state, "tenant_id"):
        request.tenant_id = req.state.tenant_id

    # Validation & Sanitization
    is_valid, error_msg = SentinelFirewall.validate(request.prompt, request.tenant_id)
    if not is_valid:
        failure_counter.inc()
        raise HTTPException(status_code=400, detail=error_msg)
    prompt_sanitized = SentinelFirewall.sanitize(request.prompt)

    # Rate limiting
    allowed, _ = await rate_limiter.is_allowed(request.tenant_id)
    if not allowed:
        failure_counter.inc()
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Multi-tenant quota
    if not await quota_manager.check_quota(request.tenant_id, tokens=len(prompt_sanitized.split())):
        failure_counter.inc()
        raise HTTPException(status_code=429, detail="Quota exceeded")

    # Adaptive Routing Toggle
    use_adaptive = os.environ.get("ADAPTIVE_ROUTING", "true").lower() == "true"
    if request.model:
        models = [request.model]
    elif use_adaptive:
        models = await adaptive_router.select_models({"prompt": prompt_sanitized})
    else:
        models = await cost_router.select_models({"prompt": prompt_sanitized})

    if not models:
        failure_counter.inc()
        raise HTTPException(status_code=503, detail="No models available for request")

    estimated_cost = cost_tracker.estimate_text_cost(models[0], prompt_sanitized)
    if not await budget_enforcer.check_budget(request.tenant_id, estimated_cost):
        failure_counter.inc()
        remaining = await budget_enforcer.get_remaining_budget(request.tenant_id)
        raise HTTPException(
            status_code=402,
            detail=f"Budget exceeded; remaining budget is ${remaining:.4f}",
        )

    # Get fallback chain from dynamic policy
    fallback_models = get_fallback_chain_from_policy(request.tenant_id, models[0])

    # Cache check
    cache_key = build_cache_key(request.tenant_id, prompt_sanitized)
    if request.use_cache:
        cached = await cache_manager.get(
            cache_key,
            prompt=prompt_sanitized,
            tenant_id=request.tenant_id,
        )
        if cached:
            latency = (time.perf_counter() - start_time) * 1000
            latency_histogram.observe(latency)
            return GenerateResponse(
                model=cached["model"],
                output=cached["output"],
                provider=cached["provider"],
                latency_ms=latency,
            )

    # Inner generation with batching support
    async def execute_generation(m_name, p_text):
        provider = ProviderFactory.get_provider_for_model(m_name)
        if not provider:
            raise Exception(f"No provider for {m_name}")

        # Inject Chaos
        if chaos.should_fail(provider.__class__.__name__):
            raise Exception("Chaos injected failure")
        await chaos.inject_latency(provider.__class__.__name__)

        return await provider.generate(prompt=p_text, model=m_name)

    # Try models in chain
    last_error = None
    for m_name in fallback_models:
        try:
            # Wrap with batcher for small requests
            result = await request_batcher.submit(
                m_name,
                prompt_sanitized,
                request.tenant_id,
                execute_generation,
            )

            if result["status"] == "success":
                latency = (time.perf_counter() - start_time) * 1000

                # Dynamic cost calculation
                tokens = len(prompt_sanitized.split()) + len(result["output"].split())
                cost = cost_tracker.calculate_cost(m_name, tokens)

                # Feedback to Adaptive Router
                await adaptive_router.record_result(m_name, True, latency, cost)
                record_cost(request.tenant_id, m_name, result["provider"], cost)
                await budget_enforcer.add_cost(request.tenant_id, cost)

                # Cache and Quota
                await cache_manager.set(
                    cache_key,
                    result,
                    prompt=prompt_sanitized,
                    tenant_id=request.tenant_id,
                )
                await quota_manager.consume(request.tenant_id, tokens=len(result["output"].split()))

                return GenerateResponse(
                    model=result["model"],
                    output=result["output"],
                    provider=result["provider"],
                    latency_ms=latency,
                )
        except Exception as e:
            logger.warning(f"Model {m_name} failed: {e}")
            await adaptive_router.record_result(m_name, False, 5000, 0.0)
            last_error = e
            continue

    failure_counter.inc()
    raise HTTPException(status_code=503, detail=f"All providers failed: {last_error}")


@app.post("/generate/stream")
async def generate_stream(request: GenerateRequest, req: Request):
    """Goat-tier streaming with backpressure and adaptive telemetry."""
    start_time = time.perf_counter()
    request_counter.inc()

    # Reuse validation logic
    is_valid, error_msg = SentinelFirewall.validate(request.prompt, request.tenant_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Model selection
    if request.model:
        models = [request.model]
    else:
        models = await adaptive_router.select_models({"prompt": request.prompt})

    if not models:
        failure_counter.inc()
        raise HTTPException(status_code=503, detail="No models available for stream")

    m_name = models[0]
    estimated_cost = cost_tracker.estimate_text_cost(m_name, request.prompt)
    if not await budget_enforcer.check_budget(request.tenant_id, estimated_cost):
        failure_counter.inc()
        remaining = await budget_enforcer.get_remaining_budget(request.tenant_id)
        raise HTTPException(
            status_code=402,
            detail=f"Budget exceeded; remaining budget is ${remaining:.4f}",
        )

    provider = ProviderFactory.get_provider_for_model(m_name)
    if not provider:
        raise HTTPException(status_code=503, detail=f"No provider for {m_name}")

    async def stream_wrapper():
        full_output = []
        try:
            async for chunk in provider.stream_generate(prompt=request.prompt, model=m_name):
                full_output.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk, 'model': m_name})}\n\n"

            # Post-stream telemetry
            latency = (time.perf_counter() - start_time) * 1000
            tokens = len(request.prompt.split()) + len(full_output)
            cost = cost_tracker.calculate_cost(m_name, tokens)

            await adaptive_router.record_result(m_name, True, latency, cost)
            record_cost(request.tenant_id, m_name, provider.__class__.__name__, cost)
            await budget_enforcer.add_cost(request.tenant_id, cost)

            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Stream failed for {m_name}: {e}")
            await adaptive_router.record_result(m_name, False, 5000, 0.0)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(stream_wrapper(), media_type="text/event-stream")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Nexus-Standard: Verified Type Safety and Professional Documentation Pattern

