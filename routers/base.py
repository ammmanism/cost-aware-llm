from abc import ABC, abstractmethod
from typing import Dict, List, Any


class BaseRouter(ABC):
    """
    Abstract base class for model selection routers.

    Routers are responsible for determining which LLM models should be
    attempted for a given request, prioritized by specific criteria
    (e.g., cost, latency, or performance).
    """

    @abstractmethod
    def select_models(self, request_data: Dict[str, Any]) -> List[str]:
        """
        Return a prioritized list of model identifiers based on the request context.

        Args:
            request_data: A dictionary containing the prompt and other metadata.

        Returns:
            A prioritized list of model names (strings) to be used for the request.
        """
        pass
