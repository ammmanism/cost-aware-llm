from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
import os
import logging
from caching.cache_manager import CacheManager
from multi_tenant.quota_manager import QuotaManager
from multi_tenant.budget_enforcer import BudgetEnforcer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# Simple admin auth (replace with proper auth in production)
ADMIN_API_KEY = "admin-secret-key"

async def verify_admin(admin_key: str = Header(..., alias="X-Admin-Key")):
    if admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return True

# Dependencies (to be injected from main app)
cache_manager: Optional[CacheManager] = None
quota_manager: Optional[QuotaManager] = None
budget_enforcer: Optional[BudgetEnforcer] = None

def init_admin_deps(
    cm: CacheManager,
    qm: QuotaManager,
    be: BudgetEnforcer
):
    global cache_manager, quota_manager, budget_enforcer
    cache_manager = cm
    quota_manager = qm
    budget_enforcer = be

class CacheInvalidateRequest(BaseModel):
    pattern: Optional[str] = None
    tenant_id: Optional[str] = None

class QuotaUpdateRequest(BaseModel):
    daily_limit: int

class BudgetUpdateRequest(BaseModel):
    monthly_budget: float

@router.post("/cache/invalidate")
async def invalidate_cache(
    request: CacheInvalidateRequest,
    _: bool = Depends(verify_admin)
):
    """Invalidate cache entries."""
    if not cache_manager:
        raise HTTPException(status_code=503, detail="Cache manager not initialized")

    if request.tenant_id:
        await cache_manager.invalidate_tenant(request.tenant_id)
        return {"message": f"Cache invalidated for tenant {request.tenant_id}"}
    elif request.pattern:
        # For Redis exact cache only
        if hasattr(cache_manager, 'invalidate_pattern'):
            count = await cache_manager.invalidate_pattern(request.pattern)
            return {"message": f"Invalidated {count} keys matching pattern"}
        else:
            return {"message": "Pattern invalidation not supported with current cache backend"}
    else:
        raise HTTPException(status_code=400, detail="Must provide pattern or tenant_id")

@router.get("/cache/stats")
async def cache_stats(_: bool = Depends(verify_admin)):
    """Get cache statistics."""
    return {
        "exact_cache": {"type": "redis" if os.environ.get("REDIS_URL") else "memory"},
        "semantic_cache": {"enabled": os.environ.get("QDRANT_URL") is not None}
    }

@router.get("/tenant/{tenant_id}/quota")
async def get_tenant_quota(tenant_id: str, _: bool = Depends(verify_admin)):
    """Get tenant quota usage."""
    if not quota_manager:
        raise HTTPException(status_code=503, detail="Quota manager not initialized")
    usage = await quota_manager.get_usage(tenant_id)
    return usage

@router.get("/tenant/{tenant_id}/budget")
async def get_tenant_budget(tenant_id: str, _: bool = Depends(verify_admin)):
    """Get tenant budget spending."""
    if not budget_enforcer.check_budget(tenant_id, 0.0): # Fake check to see if exists
        pass
    return {"tenant_id": tenant_id, "budget": budget_enforcer.default_budget}
