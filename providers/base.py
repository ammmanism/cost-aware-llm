from abc import ABC, abstractmethod
from typing import Any, Dict

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Generate a response from the LLM provider."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass