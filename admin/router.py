from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List
import logging
import os

from caching.cache_manager import CacheManager
from multi_tenant.quota_manager import QuotaManager
from multi_tenant.budget_enforcer import BudgetEnforcer
from gateway.health_checker import ProviderHealthChecker
from multi_tenant.key_manager import KeyManager
from observability.audit import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# Admin auth - load from environment
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "admin-secret-key")
key_manager = KeyManager()

async def verify_admin(admin_key: str = Header(..., alias="X-Admin-Key")):
    if admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return True

# Dependencies
cache_manager: Optional[CacheManager] = None
quota_manager: Optional[QuotaManager] = None
budget_enforcer: Optional[BudgetEnforcer] = None
health_checker: Optional[ProviderHealthChecker] = None

def init_admin_deps(cm, qm, be, hc):
    global cache_manager, quota_manager, budget_enforcer, health_checker
    cache_manager = cm
    quota_manager = qm
    budget_enforcer = be
    health_checker = hc

class CreateKeyRequest(BaseModel):
    tenant_id: str
    prefix: Optional[str] = "sk"

class KeyResponse(BaseModel):
    api_key: str
    tenant_id: str

@router.post("/keys", response_model=KeyResponse)
async def create_api_key(
    request: CreateKeyRequest,
    admin_user: str = Depends(verify_admin)
):
    """Create a new API key for a tenant."""
    try:
        api_key = await key_manager.create_key(request.tenant_id, request.prefix)
        AuditLogger.log_admin_action(
            admin_user="admin",
            action="create_api_key",
            target=request.tenant_id,
            details={"prefix": request.prefix},
        )
        return {"api_key": api_key, "tenant_id": request.tenant_id}
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to create API key")

@router.delete("/keys")
async def revoke_api_key(
    api_key: str,
    admin_user: str = Depends(verify_admin)
):
    """Revoke an API key."""
    success = await key_manager.revoke_key(api_key)
    if success:
        AuditLogger.log_admin_action(
            admin_user="admin",
            action="revoke_api_key",
            target=api_key[:8] + "...",
            details={},
        )
        return {"message": "API key revoked"}
    else:
        raise HTTPException(status_code=404, detail="API key not found")

@router.get("/keys/{tenant_id}")
async def list_tenant_keys(
    tenant_id: str,
    admin_user: str = Depends(verify_admin)
):
    """List key hashes for a tenant."""
    keys = await key_manager.list_tenant_keys(tenant_id)
    return {"tenant_id": tenant_id, "key_hashes": keys}

@router.post("/cache/invalidate")
async def invalidate_cache(
    tenant_id: Optional[str] = None,
    admin_user: str = Depends(verify_admin)
):
    if not cache_manager:
        raise HTTPException(status_code=503, detail="Cache manager not initialized")
    if tenant_id:
        await cache_manager.invalidate_tenant(tenant_id)
        AuditLogger.log_admin_action("admin", "invalidate_cache", tenant_id, {})
        return {"message": f"Cache invalidated for {tenant_id}"}
    return {"message": "No tenant_id provided"}

@router.get("/providers/status")
async def get_provider_status(admin_user: str = Depends(verify_admin)):
    if not health_checker:
        return {"status": "unknown"}
    return {
        "providers": {name: status.value for name, status in health_checker.status.items()},
        "last_check": health_checker.last_check
    }
