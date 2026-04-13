import os
from typing import Dict, Any

from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self, default_model: str = "gpt-4-turbo"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.default_model = default_model

    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        model = kwargs.get("model", self.default_model)

        if not self.api_key:
            return {
                "provider": "openai",
                "model": model,
                "output": f"[MOCK RESPONSE] {prompt}",
                "status": "success",
            }

        return {
            "provider": "openai",
            "model": model,
            "output": f"[REAL CALL PLACEHOLDER] {prompt}",
            "status": "success",
        }