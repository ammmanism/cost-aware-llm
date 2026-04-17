from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import time
import os
import json
import hashlib
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from pydantic import BaseModel

from providers.base import BaseProvider
from providers.factory import ProviderFactory
from gateway.routers.cost_aware import CostAwareRouter
from gateway.routers.latency_aware import LatencyAwareRouter
from gateway.routers.fallback import FallbackRouter
from caching.cache_manager import CacheManager
from multi_tenant.quota_manager import QuotaManager
from multi_tenant.budget_enforcer import BudgetEnforcer
from security.rate_limiter import RateLimiter
from gateway.health_checker import ProviderHealthChecker
from load_balancing.least_busy import LeastBusyBalancer
from observability.metrics.prometheus import (
    request_counter, failure_counter, latency_histogram, metrics_endpoint
)
from observability.tracing.open_telemetry import trace
from observability.logging_middleware import StructuredLoggingMiddleware
from observability.audit import AuditLogger
from admin.router import router as admin_router, init_admin_deps

# Security imports
from security.auth_middleware import APIKeyAuthMiddleware
from security.input_guard import InputGuard
from security.cors_config import configure_cors
from security.security_headers import SecurityHeadersMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global components
health_checker = ProviderHealthChecker(check_interval=30)
load_balancer = LeastBusyBalancer()
cache_manager = CacheManager()
quota_manager = QuotaManager()
budget_enforcer = BudgetEnforcer()
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

# Initialize admin dependencies
init_admin_deps(cache_manager, quota_manager, budget_enforcer, health_checker)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting LLM Gateway...")
    ProviderFactory.get_all_providers()
    await health_checker.start()
    logger.info("Gateway ready")
    yield
    await health_checker.stop()
    logger.info("Gateway shutdown")

app = FastAPI(title="LLM Gateway", version="5.0.0", lifespan=lifespan)

# Security middleware stack (order matters)
configure_cors(app)  # CORS first
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    APIKeyAuthMiddleware,
    exclude_paths={"/health", "/metrics", "/docs", "/openapi.json", "/redoc", "/admin"}
)
app.add_middleware(StructuredLoggingMiddleware)

# Include admin router
app.include_router(admin_router)

# Routers
cost_router = CostAwareRouter()
latency_router = LatencyAwareRouter()
fallback_router = FallbackRouter()

class GenerateRequest(BaseModel):
    prompt: str
    tenant_id: Optional[str] = "default"  # Overridden by auth if present
    use_cache: Optional[bool] = True
    prefer_latency: Optional[bool] = False
    model: Optional[str] = None
    stream: Optional[bool] = False

class GenerateResponse(BaseModel):
    model: str
    output: str
    provider: str
    latency_ms: float

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "providers": {name: status.value for name, status in health_checker.status.items()}
    }

@app.get("/metrics")
async def get_metrics():
    return metrics_endpoint()

@app.post("/generate")
@trace
async def generate(request: GenerateRequest, req: Request):
    start_time = time.perf_counter()
    request_counter.inc()

    # Override tenant_id from authenticated context if available
    if hasattr(req.state, "tenant_id"):
        request.tenant_id = req.state.tenant_id

    # Input validation
    is_valid, error_msg = InputGuard.validate(request.prompt, request.tenant_id)
    if not is_valid:
        failure_counter.inc()
        raise HTTPException(status_code=400, detail=error_msg)
    prompt_sanitized = InputGuard.sanitize(request.prompt)

    # Rate limiting
    allowed, remaining = await rate_limiter.is_allowed(request.tenant_id)
    if not allowed:
        failure_counter.inc()
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Multi-tenant checks
    estimated_input_tokens = len(prompt_sanitized.split())
    if not await quota_manager.check_quota(request.tenant_id, tokens=estimated_input_tokens):
        failure_counter.inc()
        AuditLogger.log_request(
            tenant_id=request.tenant_id,
            request_id=getattr(req.state, "request_id", "unknown"),
            endpoint="/generate",
            prompt_hash=hashlib.md5(prompt_sanitized.encode()).hexdigest(),
            prompt_length=len(prompt_sanitized),
            model="n/a",
            status="quota_exceeded",
            latency_ms=(time.perf_counter() - start_time) * 1000,
            error="Quota exceeded"
        )
        raise HTTPException(status_code=429, detail="Quota exceeded")

    if not await budget_enforcer.check_budget(request.tenant_id, estimated_cost=0.01):
        failure_counter.inc()
        AuditLogger.log_request(
            tenant_id=request.tenant_id,
            request_id=getattr(req.state, "request_id", "unknown"),
            endpoint="/generate",
            prompt_hash=hashlib.md5(prompt_sanitized.encode()).hexdigest(),
            prompt_length=len(prompt_sanitized),
            model="n/a",
            status="budget_exceeded",
            latency_ms=(time.perf_counter() - start_time) * 1000,
            error="Budget exceeded"
        )
        raise HTTPException(status_code=402, detail="Budget exceeded")

    # Cache check
    cache_key = f"cache:{request.tenant_id}:{hashlib.md5(prompt_sanitized.encode()).hexdigest()}"
    if request.use_cache:
        cached = await cache_manager.get(cache_key, prompt=prompt_sanitized, tenant_id=request.tenant_id)
        if cached:
            latency = (time.perf_counter() - start_time) * 1000
            latency_histogram.observe(latency)
            logger.info(f"Cache hit for tenant {request.tenant_id}")
            AuditLogger.log_request(
                tenant_id=request.tenant_id,
                request_id=getattr(req.state, "request_id", "unknown"),
                endpoint="/generate",
                prompt_hash=hashlib.md5(prompt_sanitized.encode()).hexdigest(),
                prompt_length=len(prompt_sanitized),
                model=cached["model"],
                status="cache_hit",
                latency_ms=latency,
            )
            return GenerateResponse(
                model=cached["model"],
                output=cached["output"],
                provider=cached["provider"],
                latency_ms=latency
            )

    # Model selection
    if request.model:
        models = [request.model]
    else:
        if request.prefer_latency:
            models = latency_router.select_models({"prompt": prompt_sanitized})
        else:
            models = cost_router.select_models({"prompt": prompt_sanitized})

    fallback_models = fallback_router.get_fallback_chain(models)
    healthy_providers = health_checker.get_healthy_providers()

    viable_models = []
    for model in fallback_models:
        provider = ProviderFactory.get_provider_for_model(model)
        if not provider: continue
        provider_name = provider.__class__.__name__.lower().replace("provider", "")
        if provider_name in healthy_providers or not healthy_providers:
            viable_models.append(model)

    if not viable_models:
        failure_counter.inc()
        raise HTTPException(status_code=503, detail="No healthy providers available")

    # Try providers
    last_error = None
    for model_name in viable_models:
        provider = ProviderFactory.get_provider_for_model(model_name)
        if not provider:
            continue

        try:
            result = await provider.generate(prompt=prompt_sanitized, model=model_name)
            if result["status"] == "success":
                # Cache result
                await cache_manager.set(
                    cache_key,
                    {"model": result["model"], "output": result["output"], "provider": result["provider"]},
                    prompt=prompt_sanitized,
                    tenant_id=request.tenant_id
                )
                output_tokens = len(result["output"].split())
                await quota_manager.consume(request.tenant_id, tokens=output_tokens)
                await budget_enforcer.add_cost(request.tenant_id, cost=0.01)
                latency = (time.perf_counter() - start_time) * 1000
                latency_histogram.observe(latency)

                AuditLogger.log_request(
                    tenant_id=request.tenant_id,
                    request_id=getattr(req.state, "request_id", "unknown"),
                    endpoint="/generate",
                    prompt_hash=hashlib.md5(prompt_sanitized.encode()).hexdigest(),
                    prompt_length=len(prompt_sanitized),
                    model=result["model"],
                    status="success",
                    latency_ms=latency,
                )

                return GenerateResponse(
                    model=result["model"],
                    output=result["output"],
                    provider=result["provider"],
                    latency_ms=latency
                )
        except Exception as e:
            logger.warning(f"Provider {model_name} failed: {e}")
            last_error = e
            continue

    failure_counter.inc()
    latency = (time.perf_counter() - start_time) * 1000
    AuditLogger.log_request(
        tenant_id=request.tenant_id,
        request_id=getattr(req.state, "request_id", "unknown"),
        endpoint="/generate",
        prompt_hash=hashlib.md5(prompt_sanitized.encode()).hexdigest(),
        prompt_length=len(prompt_sanitized),
        model="n/a",
        status="error",
        latency_ms=latency,
        error=str(last_error),
    )
    raise HTTPException(status_code=503, detail=f"All providers failed: {last_error}")

@app.post("/generate/stream")
async def generate_stream(request: GenerateRequest, req: Request):
    """Streaming endpoint with SSE."""
    start_time = time.perf_counter()
    request_counter.inc()

    if hasattr(req.state, "tenant_id"):
        request.tenant_id = req.state.tenant_id

    # Input validation
    is_valid, error_msg = InputGuard.validate(request.prompt, request.tenant_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    prompt_sanitized = InputGuard.sanitize(request.prompt)

    allowed, _ = await rate_limiter.is_allowed(request.tenant_id)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    if not await quota_manager.check_quota(request.tenant_id, tokens=len(prompt_sanitized.split())):
        raise HTTPException(status_code=429, detail="Quota exceeded")

    # Model selection
    if request.model:
        models = [request.model]
    else:
        models = cost_router.select_models({"prompt": prompt_sanitized})

    fallback_models = fallback_router.get_fallback_chain(models)
    healthy_providers = health_checker.get_healthy_providers()

    viable_models = []
    for model in fallback_models:
        provider = ProviderFactory.get_provider_for_model(model)
        if not provider: continue
        provider_name = provider.__class__.__name__.lower().replace("provider", "")
        if provider_name in healthy_providers or not healthy_providers:
            viable_models.append(model)

    if not viable_models:
        raise HTTPException(status_code=503, detail="No healthy providers available")

    async def event_generator():
        full_response = []
        provider_used = None
        model_used = None
        stream_error = None

        for model_name in viable_models:
            provider = ProviderFactory.get_provider_for_model(model_name)
            if not provider:
                continue
            try:
                provider_used = provider.__class__.__name__.lower().replace("provider", "")
                model_used = model_name
                async for chunk in provider.stream_generate(prompt=prompt_sanitized, model=model_name):
                    full_response.append(chunk)
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                break
            except Exception as e:
                logger.warning(f"Streaming provider {model_name} failed: {e}")
                stream_error = str(e)
                continue
        else:
            yield f"data: {json.dumps({'error': 'All providers failed'})}\n\n"
            yield "data: [DONE]\n\n"
            # Audit log failure
            AuditLogger.log_request(
                tenant_id=request.tenant_id,
                request_id=getattr(req.state, "request_id", "unknown"),
                endpoint="/generate/stream",
                prompt_hash=hashlib.md5(prompt_sanitized.encode()).hexdigest(),
                prompt_length=len(prompt_sanitized),
                model="n/a",
                status="error",
                latency_ms=(time.perf_counter() - start_time) * 1000,
                error=stream_error or "All providers failed",
            )
            return

        full_output = "".join(full_response)
        cache_key = f"cache:{request.tenant_id}:{hashlib.md5(prompt_sanitized.encode()).hexdigest()}"
        await cache_manager.set(
            cache_key,
            {"model": model_used, "output": full_output, "provider": provider_used},
            prompt=prompt_sanitized,
            tenant_id=request.tenant_id
        )

        await quota_manager.consume(request.tenant_id, tokens=len(full_output.split()))
        await budget_enforcer.add_cost(request.tenant_id, cost=0.01)

        latency = (time.perf_counter() - start_time) * 1000
        latency_histogram.observe(latency)
        AuditLogger.log_request(
            tenant_id=request.tenant_id,
            request_id=getattr(req.state, "request_id", "unknown"),
            endpoint="/generate/stream",
            prompt_hash=hashlib.md5(prompt_sanitized.encode()).hexdigest(),
            prompt_length=len(prompt_sanitized),
            model=model_used,
            status="success",
            latency_ms=latency,
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    failure_counter.inc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": getattr(request.state, "request_id", None)}
    )
