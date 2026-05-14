from typing import List, Any
import itertools


class RoundRobinBalancer:
    """
    Standard load balancer that cycles through available providers sequentially.

    This is the simplest load balancing strategy, distributing requests
    evenly across all providers regardless of their current load.
    """

    def __init__(self, providers: List[Any] = None):
        self.providers = providers or []
        self._cycle = itertools.cycle(self.providers) if self.providers else None

    def get_next(self) -> Any:
        """
        Get the next provider in the rotation.

        Returns:
            The next provider instance, or None if no providers are available.
        """
        if not self._cycle:
            return None
        return next(self._cycle)
