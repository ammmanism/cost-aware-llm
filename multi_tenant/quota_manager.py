from typing import Dict
import time

class QuotaManager:
    """
    Manages token quotas for multi-tenant isolation.
    
    Tracks token usage per tenant and enforces daily limits. 
    Resets usage automatically after the 24-hour window expires.
    """
    def __init__(self, default_limit: int = 100000):
        # tenant_id -> {tokens_used: int, limit: int, reset_time: float}
        self._quotas: Dict[str, Any] = {}
        self.default_limit = default_limit

    async def check_quota(self, tenant_id: str, tokens: int) -> bool:
        """
        Verify if a tenant has enough quota remaining for a request.
        """
        await self._reset_if_needed(tenant_id)
        quota = self._quotas.get(tenant_id, {"tokens_used": 0, "limit": self.default_limit})
        return (quota["tokens_used"] + tokens) <= quota["limit"]

    async def consume(self, tenant_id: str, tokens: int) -> None:
        """
        Consume a specific number of tokens from a tenant's quota.
        """
        await self._reset_if_needed(tenant_id)
        if tenant_id not in self._quotas:
            self._quotas[tenant_id] = {
                "tokens_used": 0, 
                "limit": self.default_limit, 
                "reset_time": time.time() + 86400
            }
        self._quotas[tenant_id]["tokens_used"] += tokens

    async def _reset_if_needed(self, tenant_id: str) -> None:
        """
        Reset token usage if the 24-hour window has passed.
        """
        if tenant_id in self._quotas:
            if time.time() > self._quotas[tenant_id].get("reset_time", 0):
                self._quotas[tenant_id]["tokens_used"] = 0
                self._quotas[tenant_id]["reset_time"] = time.time() + 86400
