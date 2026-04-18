from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os

router = APIRouter(prefix="/admin/fallback", tags=["fallback-policies"])

class FallbackRule(BaseModel):
    primary_model: str
    fallback_models: List[str]
    priority: int = 0

class FallbackPolicy(BaseModel):
    name: str
    rules: List[FallbackRule]
    default_chain: List[str] = ["gpt-3.5-turbo"]

# In-memory store (use Redis in production)
_policies: Dict[str, FallbackPolicy] = {
    "default": FallbackPolicy(
        name="default",
        rules=[],
        default_chain=["gpt-3.5-turbo", "claude-3-haiku", "llama-3-8b"]
    )
}

@router.get("/policies")
async def list_policies():
    return {"policies": list(_policies.keys())}

@router.get("/policies/{policy_name}")
async def get_policy(policy_name: str):
    if policy_name not in _policies:
        raise HTTPException(status_code=404, detail="Policy not found")
    return _policies[policy_name]

@router.put("/policies/{policy_name}")
async def update_policy(policy_name: str, policy: FallbackPolicy):
    _policies[policy_name] = policy
    return {"message": "Policy updated"}

@router.post("/policies/{policy_name}/rules")
async def add_rule(policy_name: str, rule: FallbackRule):
    if policy_name not in _policies:
        _policies[policy_name] = FallbackPolicy(name=policy_name, rules=[], default_chain=[])
    _policies[policy_name].rules.append(rule)
    return {"message": "Rule added"}

@router.delete("/policies/{policy_name}/rules/{primary_model}")
async def delete_rule(policy_name: str, primary_model: str):
    if policy_name not in _policies:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy = _policies[policy_name]
    policy.rules = [r for r in policy.rules if r.primary_model != primary_model]
    return {"message": "Rule deleted"}

def get_fallback_chain_from_policy(policy_name: str, model: str) -> List[str]:
    """Get fallback chain for a given model under a policy."""
    if policy_name not in _policies:
        policy_name = "default"
    policy = _policies.get(policy_name)
    if not policy:
         return [model, "gpt-3.5-turbo"]
    for rule in policy.rules:
        if rule.primary_model == model:
            return [model] + rule.fallback_models
    return [model] + policy.default_chain
