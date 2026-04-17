from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncIterator

class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate a complete response from the LLM.

        Args:
            prompt: Input text prompt.
            **kwargs: Additional provider-specific arguments.

        Returns:
            Dictionary containing provider, model, output, status.
        """
        pass

    @abstractmethod
    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """
        Stream response tokens as they are generated.

        Args:
            prompt: Input text prompt.
            **kwargs: Additional provider-specific arguments.

        Yields:
            Token chunks as strings.
        """
        pass