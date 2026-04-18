from providers.openai import OpenAIProvider
from providers.anthropic import AnthropicProvider
from providers.gemini import GeminiProvider
from providers.together import TogetherProvider
from providers.groq import GroqProvider

class ProviderFactory:
    """Factory for LLM providers."""
    _providers = {
        "openai": OpenAIProvider(),
        "anthropic": AnthropicProvider(),
        "google": GeminiProvider(),
        "together": TogetherProvider(),
        "groq": GroqProvider()
    }

    @classmethod
    def get_all_providers(cls):
        return cls._providers

    @classmethod
    def get_provider_for_model(cls, model_name: str):
        if "gpt" in model_name:
            return cls._providers["openai"]
        if "claude" in model_name:
            return cls._providers["anthropic"]
        if "gemini" in model_name:
            return cls._providers["google"]
        if "llama" in model_name or "mixtral" in model_name:
            return cls._providers["together"]
        return None
