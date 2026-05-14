from providers.openai import OpenAIProvider
from providers.anthropic import AnthropicProvider
from providers.gemini import GeminiProvider
from providers.together import TogetherProvider
from providers.groq import GroqProvider
from providers.vllm import VLLMProvider
from typing import Dict, Any, Optional, Set

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
        "vllm": VLLMProvider()
    }
    
    _disabled_providers: Set[str] = set()

    @classmethod
    def get_all_providers(cls) -> Dict[str, Any]:
        """Retrieve all registered provider instances."""
        return {k: v for k, v in cls._providers.items() if k not in cls._disabled_providers}

    @classmethod
    def disable_provider(cls, name: str):
        """Temporarily disable a provider."""
        cls._disabled_providers.add(name)

    @classmethod
    def enable_provider(cls, name: str):
        """Re-enable a provider."""
        cls._disabled_providers.discard(name)

    @classmethod
    def get_provider_for_model(cls, model_name: str) -> Optional[Any]:
        """Identify the correct provider based on the requested model name."""
        provider_key = None
        if "gpt" in model_name:
            provider_key = "openai"
        elif "claude" in model_name:
            provider_key = "anthropic"
        elif "gemini" in model_name:
            provider_key = "google"
        elif "llama" in model_name or "mixtral" in model_name:
            provider_key = "together"
        elif "vllm" in model_name or "local" in model_name:
            provider_key = "vllm"
            
        if provider_key and provider_key not in cls._disabled_providers:
            return cls._providers.get(provider_key)
        return None

