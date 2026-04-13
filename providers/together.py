from typing import Any, Dict
from providers.base import LLMProvider

class TogetherProvider(LLMProvider):
    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        return {"text": f"Together Stub: {prompt}"}

    @property
    def name(self) -> str:
        return "together"
