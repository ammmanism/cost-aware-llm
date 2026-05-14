from providers.openai import OpenAIProvider
from providers.anthropic import AnthropicProvider
from providers.gemini import GeminiProvider
from providers.together import TogetherProvider
from providers.groq import GroqProvider
from providers.vllm import VLLMProvider
from typing import Dict, Any, Optional


class ProviderFactory:
    """
    Singleton factory for managing LLM provider instances.

    This factory handles the mapping between model names and their respective
    provider implementations, ensuring that requests are routed correctly.
    """

    _providers = {
        "openai": OpenAIProvider(),
        "anthropic": AnthropicProvider(),
        "google": GeminiProvider(),
        "together": TogetherProvider(),
        "groq": GroqProvider(),
        "vllm": VLLMProvider(),
    }

    @classmethod
    def get_all_providers(cls) -> Dict[str, Any]:
        """Retrieve all registered provider instances."""
        return cls._providers

    @classmethod
    def get_provider_for_model(cls, model_name: str) -> Optional[Any]:
        """
        Identify the correct provider based on the requested model name.

        Args:
            model_name: The name of the LLM model (e.g., 'gpt-4').

        Returns:
            The provider instance responsible for the model, or None.
        """
        if "gpt" in model_name:
            return cls._providers["openai"]
        if "claude" in model_name:
            return cls._providers["anthropic"]
        if "gemini" in model_name:
            return cls._providers["google"]
        if "llama" in model_name or "mixtral" in model_name:
            return cls._providers["together"]
        if "vllm" in model_name or "local" in model_name:
            return cls._providers["vllm"]
        return None
