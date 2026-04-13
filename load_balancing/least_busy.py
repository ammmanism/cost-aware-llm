from typing import List, Any
import asyncio

class LeastBusyBalancer:
    def __init__(self, providers: List[Any]):
        self.providers = providers
        self._active_requests = {p: 0 for p in providers}
        self._lock = asyncio.Lock()

    async def get_provider(self) -> Any:
        async with self._lock:
            # Find provider with minimum active requests
            min_provider = min(self.providers, key=lambda p: self._active_requests[p])
            self._active_requests[min_provider] += 1
            return min_provider

    async def release_provider(self, provider: Any):
        async with self._lock:
            self._active_requests[provider] -= 1
