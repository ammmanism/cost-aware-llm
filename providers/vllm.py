from typing import Any, Dict
from providers.base import LLMProvider

class VLLMProvider(LLMProvider):
    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        return {"text": f"vLLM Stub: {prompt}"}

    @property
    def name(self) -> str:
        return "vllm"
