from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseProvider(ABC):
    """
    Abstract base class for all LLM providers.
    """

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Generate response from LLM.

        Args:
            prompt (str): Input prompt
            **kwargs: Provider-specific parameters

        Returns:
            Dict[str, Any]: Standardized response
        """
        pass