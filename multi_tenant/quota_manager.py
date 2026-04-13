from typing import Dict
import time

class QuotaManager:
    def __init__(self):
        # tenant_id -> {tokens_used: int, limit: int, reset_time: float}
        self._quotas: Dict[str, Dict] = {}
        self.default_limit = 10000  # tokens per day

    def check_quota(self, tenant_id: str, tokens: int) -> bool:
        self._reset_if_needed(tenant_id)
        quota = self._quotas.get(tenant_id, {"tokens_used": 0, "limit": self.default_limit})
        return (quota["tokens_used"] + tokens) <= quota["limit"]

    def consume(self, tenant_id: str, tokens: int):
        self._reset_if_needed(tenant_id)
        if tenant_id not in self._quotas:
            self._quotas[tenant_id] = {"tokens_used": 0, "limit": self.default_limit, "reset_time": time.time() + 86400}
        self._quotas[tenant_id]["tokens_used"] += tokens

    def _reset_if_needed(self, tenant_id: str):
        if tenant_id in self._quotas:
            if time.time() > self._quotas[tenant_id].get("reset_time", 0):
                self._quotas[tenant_id]["tokens_used"] = 0
                self._quotas[tenant_id]["reset_time"] = time.time() + 86400
