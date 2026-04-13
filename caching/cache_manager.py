from typing import Optional, Any
from caching.exact_cache import ExactCache
from caching.semantic_cache import SemanticCache

class CacheManager:
    def __init__(self):
        self.exact = ExactCache()
        self.semantic = SemanticCache()

    def get(self, prompt: str) -> Optional[Any]:
        # Try exact first
        result = self.exact.get(prompt)
        if result:
            return result
        # then semantic
        return self.semantic.get(prompt)

    def set(self, prompt: str, response: Any):
        self.exact.set(prompt, response)
        self.semantic.set(prompt, response)
