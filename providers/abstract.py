from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncIterator


class BaseProvider(ABC):
    """
    Foundational interface for all LLM provider integrations.

    This abstract class defines the standard contract that every provider
    (OpenAI, Anthropic, Gemini, etc.) must implement to be compatible with
    the gateway's routing and load balancing logic.
    """

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Generate a full text completion for the given prompt.

        Args:
            prompt: The input text to send to the model.
            **kwargs: Configuration overrides (temperature, max_tokens, etc.).

        Returns:
            A standard dictionary containing the model's response and metadata.
        """
        pass

    @abstractmethod
    async def stream_generate(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        """
        Stream the completion response token by token.

        Args:
            prompt: The input text to send to the model.
            **kwargs: Configuration overrides.

        Yields:
            Individual token strings as they are received from the provider.
        """
        pass
