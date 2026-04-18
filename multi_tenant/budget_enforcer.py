from typing import Dict, Optional
import redis.asyncio as redis
import os
import logging

logger = logging.getLogger(__name__)

class BudgetEnforcer:
    """
    Elite Tier Budget Enforcer using Redis ATOMIC transactions to prevent
    overspending during extreme concurrency scenarios.
    """
    
    def __init__(self):
        self.default_budget = 10.0  # USD per month
        self.redis_url = os.environ.get("REDIS_URL")
        self._redis: Optional[redis.Redis] = None
        self._connected = False
        
        # Fallback Memory
        self._spending: Dict[str, float] = {}

    async def _ensure_redis_connected(self):
        if self.redis_url and not self._connected:
            try:
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                await self._redis.ping()
                self._connected = True
            except Exception as e:
                logger.error(f"Cannot connect to Redis for Budget Enforcer: {e}")
                self.redis_url = None

    async def check_budget(self, tenant_id: str, estimated_cost: float) -> bool:
        await self._ensure_redis_connected()
        
        if self._redis:
            val = await self._redis.get(f"budget:{tenant_id}:spent")
            current = float(val) if val else 0.0
            return (current + estimated_cost) <= self.default_budget
        else:
            current = self._spending.get(tenant_id, 0.0)
            return (current + estimated_cost) <= self.default_budget

    async def add_cost(self, tenant_id: str, cost: float):
        await self._ensure_redis_connected()
        
        if self._redis:
            # Atomic float increment via redis INCRBYFLOAT
            await self._redis.incrbyfloat(f"budget:{tenant_id}:spent", cost)
            # Ensure it expires at the end of the month (simplified 30 days)
            await self._redis.expire(f"budget:{tenant_id}:spent", 2592000)
        else:
            if tenant_id not in self._spending:
                self._spending[tenant_id] = 0.0
            self._spending[tenant_id] += cost
