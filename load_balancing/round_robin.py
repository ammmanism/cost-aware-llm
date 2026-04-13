from typing import List, Any
import itertools

class RoundRobinBalancer:
    def __init__(self, providers: List[Any]):
        self.providers = providers
        self._cycle = itertools.cycle(providers)

    def get_next(self) -> Any:
        return next(self._cycle)
