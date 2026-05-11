from typing import List, Any
import asyncio

class LeastBusyBalancer:
    """
    Load balancer that routes requests to the provider with the fewest active tasks.
    
    This strategy ensures that no single provider is overwhelmed while others 
    are idle, optimizing throughput and response times.
    """
    def __init__(self, providers: List[Any] = None):
        self.providers = providers or []
        self._active_requests = {p: 0 for p in self.providers}
        self._lock = asyncio.Lock()

    async def get_provider(self) -> Any:
        """
        Select the provider with the minimum number of concurrent requests.

        Returns:
            The selected provider instance, or None if no providers are available.
        """
        async with self._lock:
            if not self.providers:
                return None
            
            # Find provider with minimum active requests
            min_provider = min(self.providers, key=lambda p: self._active_requests.get(p, 0))
            self._active_requests[min_provider] = self._active_requests.get(min_provider, 0) + 1
            return min_provider

    async def release_provider(self, provider: Any) -> None:
        """
        Decrement the active request count for a provider after task completion.

        Args:
            provider: The provider instance to release.
        """
        async with self._lock:
            if provider in self._active_requests:
                self._active_requests[provider] = max(0, self._active_requests[provider] - 1)
