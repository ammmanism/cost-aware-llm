from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseRouter(ABC):
    @abstractmethod
    def route(self, request: Dict[str, Any]) -> str:
        """Decide which model/provider to use."""
        pass
