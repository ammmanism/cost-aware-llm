from typing import Any, Optional
from caching.exact_cache import ExactCache

class CacheManager:
    def __init__(self, default_ttl: int = 3600):
        self.cache = ExactCache()
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Optional[Any]:
        return await self.cache.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        ttl = ttl if ttl is not None else self.default_ttl
        await self.cache.set(key, value, ttl)

    async def invalidate(self, key: str):
        await self.cache.delete(key)
