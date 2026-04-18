import os
import logging
from typing import Any, Optional
from caching.redis_cache import RedisCache
from caching.exact_cache import ExactCache
from caching.semantic_cache import SemanticCache

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Multi-level cache manager:
    - L1: Exact match (Redis or in-memory)
    - L2: Semantic similarity (Qdrant vector DB)
    """

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._use_redis = os.environ.get("REDIS_URL") is not None
        self._use_semantic = os.environ.get("QDRANT_URL") is not None

        # L1 exact cache
        if self._use_redis:
            self.exact_cache = RedisCache(redis_url=os.environ["REDIS_URL"])
            self._redis_connected = False
        else:
            self.exact_cache = ExactCache()
            logger.warning("No REDIS_URL, using in-memory exact cache")

        # L2 semantic cache
        if self._use_semantic:
            self.semantic_cache = SemanticCache(
                qdrant_url=os.environ.get("QDRANT_URL", "http://localhost:6333"),
                similarity_threshold=float(os.environ.get("SEMANTIC_THRESHOLD", "0.95"))
            )
        else:
            self.semantic_cache = None
            logger.info("Semantic cache disabled (set QDRANT_URL to enable)")

    async def _ensure_redis_connected(self):
        if self._use_redis and not self._redis_connected:
            await self.exact_cache.connect()
            self._redis_connected = True

    async def get(self, key: str, prompt: Optional[str] = None, tenant_id: str = "default") -> Optional[Any]:
        """Get from cache with Dogpile/Stampede protection."""
        if not hasattr(self, "_locks"):
            import asyncio
            self._locks = {}
            
        await self._ensure_redis_connected()

        # Try exact match first
        exact_value = await self.exact_cache.get(key)
        if exact_value: return exact_value

        # Use an asyncio lock to prevent 'Cache Stampede' on simultaneous identical requests
        import asyncio
        if key not in self._locks: self._locks[key] = asyncio.Lock()
        
        async with self._locks[key]:
            # Double check exact cache once acquired
            exact_value = await self.exact_cache.get(key)
            if exact_value: return exact_value

            if self.semantic_cache and prompt:
                semantic_value = await self.semantic_cache.get(prompt, tenant_id)
                if semantic_value:
                    logger.debug("Semantic cache hit (recovered in locked region)")
                    await self.exact_cache.set(key, semantic_value, self.default_ttl)
                    return semantic_value

        # Clean lock dict occasionally (simplified)
        if len(self._locks) > 10000: self._locks.clear()
        
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None, prompt: Optional[str] = None, tenant_id: str = "default"):
        """Store in both exact and semantic caches."""
        ttl = ttl or self.default_ttl
        await self._ensure_redis_connected()

        # Store in exact cache
        await self.exact_cache.set(key, value, ttl)

        # Store in semantic cache if enabled and prompt provided
        if self.semantic_cache and prompt:
            await self.semantic_cache.set(prompt, tenant_id, value, ttl)

    async def invalidate(self, key: str):
        await self._ensure_redis_connected()
        await self.exact_cache.delete(key)

    async def invalidate_tenant(self, tenant_id: str):
        """Invalidate all cache for a tenant (semantic only)."""
        if self.semantic_cache:
            await self.semantic_cache.invalidate_tenant(tenant_id)
