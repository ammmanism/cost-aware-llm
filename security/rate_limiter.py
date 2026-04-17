import time
from typing import Dict, Tuple

class RateLimiter:
    """Mock Rate Limiter for LLM Gateway."""
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}

    async def is_allowed(self, tenant_id: str) -> Tuple[bool, int]:
        now = time.time()
        if tenant_id not in self.requests:
            self.requests[tenant_id] = []
        
        self.requests[tenant_id] = [req for req in self.requests[tenant_id] if now - req < self.window_seconds]
        
        if len(self.requests[tenant_id]) < self.max_requests:
            self.requests[tenant_id].append(now)
            return True, self.max_requests - len(self.requests[tenant_id])
        
        return False, 0
