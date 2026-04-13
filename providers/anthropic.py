from typing import Any, Dict
from providers.base import LLMProvider

class AnthropicProvider(LLMProvider):
    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        return {"text": f"Anthropic Stub: {prompt}"}

    @property
    def name(self) -> str:
        return "anthropic"
