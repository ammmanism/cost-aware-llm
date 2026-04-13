from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate a response from the LLM.

        Args:
            prompt: Input text prompt.
            **kwargs: Additional provider-specific arguments (e.g., model, temperature).

        Returns:
            Dictionary containing at least:
                - provider: str
                - model: str
                - output: str
                - status: str ("success" or "error")
        """
        pass