from typing import List

from fastapi import APIRouter

router = APIRouter(prefix="/admin/fallback", tags=["admin"])


def get_fallback_chain_from_policy(tenant_id: str, primary_model: str) -> List[str]:
    """Retrieve the fallback chain for a given tenant and primary model."""
    # Mock logic: return the primary model followed by a safe default
    return [primary_model, "gpt-3.5-turbo", "claude-3-haiku"]


@router.get("/policies")
async def list_policies():
    return {"policies": []}
