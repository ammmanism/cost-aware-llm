from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import logging
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel

from providers.openai import OpenAIProvider
from gateway.routers.cost_aware import CostAwareRouter
from gateway.routers.latency_aware import LatencyAwareRouter
from gateway.routers.fallback import FallbackRouter
from caching.cache_manager import CacheManager
from multi_tenant.quota_manager import QuotaManager
from multi_tenant.budget_enforcer import BudgetEnforcer
from observability.metrics.prometheus import (
    request_counter, failure_counter, latency_histogram
)
from observability.tracing.open_telemetry import trace

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Gateway")

# Initialize components
provider = OpenAIProvider()
cost_router = CostAwareRouter()
latency_router = LatencyAwareRouter()
fallback_router = FallbackRouter()
cache_manager = CacheManager()
quota_manager = QuotaManager()
budget_enforcer = BudgetEnforcer()

class GenerateRequest(BaseModel):
    prompt: str
    tenant_id: Optional[str] = "default"
    use_cache: Optional[bool] = True

class GenerateResponse(BaseModel):
    model: str
    output: str
    provider: str
    latency_ms: float

@app.post("/generate", response_model=GenerateResponse)
@trace
async def generate(request: GenerateRequest, req: Request):
    start_time = time.time()
    request_counter.inc()

    # Multi-tenant checks
    if not quota_manager.check_quota(request.tenant_id, tokens=len(request.prompt.split())):
        failure_counter.inc()
        raise HTTPException(status_code=429, detail="Quota exceeded")
    if not budget_enforcer.check_budget(request.tenant_id, estimated_cost=0.01):
        failure_counter.inc()
        raise HTTPException(status_code=402, detail="Budget exceeded")

    # Check cache
    cache_key = f"{request.tenant_id}:{request.prompt}"
    if request.use_cache:
        cached = await cache_manager.get(cache_key)
        if cached:
            latency = (time.time() - start_time) * 1000
            latency_histogram.observe(latency)
            return GenerateResponse(
                model=cached["model"],
                output=cached["output"],
                provider=cached["provider"],
                latency_ms=latency
            )

    # Router selection (cost-aware primary, fallback list)
    models = cost_router.select_models({"prompt": request.prompt})
    fallback_models = fallback_router.get_fallback_chain(models)

    # Try providers in fallback order
    last_error = None
    for model_name in fallback_models:
        try:
            result = await provider.generate(prompt=request.prompt, model=model_name)
            if result["status"] == "success":
                # Cache result
                await cache_manager.set(cache_key, {
                    "model": result["model"],
                    "output": result["output"],
                    "provider": result["provider"]
                })
                # Update quota
                quota_manager.consume(request.tenant_id, tokens=len(result["output"].split()))
                latency = (time.time() - start_time) * 1000
                latency_histogram.observe(latency)
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
    raise HTTPException(status_code=503, detail=f"All providers failed: {last_error}")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    failure_counter.inc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
