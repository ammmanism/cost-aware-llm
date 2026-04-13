from abc import ABC, abstractmethod
from typing import Dict, List, Any

class BaseRouter(ABC):
    """Base class for model selection routers."""

    @abstractmethod
    def select_models(self, request: Dict[str, Any]) -> List[str]:
        """
        Return a prioritized list of model identifiers.

        Args:
            request: Request context (may contain prompt, etc.)

        Returns:
            List of model names in order of preference.
        """
        pass
