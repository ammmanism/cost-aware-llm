import os
import logging
from typing import Any, Optional
from caching.redis_cache import RedisCache
from caching.exact_cache import ExactCache
from caching.semantic_cache import SemanticCache

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Orchestrates multi-level caching for LLM responses.
    
    Levels:
    - L1 (Exact): Redis or In-memory hash map for identical prompts.
    - L2 (Semantic): Vector database (Qdrant) for similar prompts.
    
    Includes protection against 'Cache Stampede' using localized locking.
    """

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._use_redis = os.environ.get("REDIS_URL") is not None
        self._use_semantic = os.environ.get("QDRANT_URL") is not None
        self._redis_connected = False
        self._locks: Dict[str, asyncio.Lock] = {}

        # L1 exact cache initialization
        if self._use_redis:
            self.exact_cache = RedisCache(redis_url=os.environ["REDIS_URL"])
        else:
            self.exact_cache = ExactCache()
            logger.warning("No REDIS_URL found. Falling back to in-memory exact cache (L1).")

        # L2 semantic cache initialization
        if self._use_semantic:
            self.semantic_cache = SemanticCache(
                qdrant_url=os.environ.get("QDRANT_URL", "http://localhost:6333"),
                similarity_threshold=float(os.environ.get("SEMANTIC_THRESHOLD", "0.95"))
            )
        else:
            self.semantic_cache = None
            logger.info("Semantic cache (L2) is disabled. Set QDRANT_URL to enable.")

    async def _ensure_redis_connected(self) -> None:
        """Helper to lazy-connect to the L1 Redis cache."""
        if self._use_redis and not self._redis_connected:
            try:
                await self.exact_cache.connect()
                self._redis_connected = True
            except Exception as e:
                logger.error(f"Failed to connect to L1 Redis: {e}")
                # Don't try again immediately to avoid spamming
                self._use_redis = False

    async def get(self, key: str, prompt: Optional[str] = None, tenant_id: str = "default") -> Optional[Any]:
        """
        Retrieve a value from the multi-level cache.

        Args:
            key: The unique cache key for exact matches.
            prompt: The original prompt for semantic lookup.
            tenant_id: The tenant associated with the request.

        Returns:
            The cached value if found, else None.
        """
        await self._ensure_redis_connected()

        # 1. Attempt L1 Exact Match
        exact_value = await self.exact_cache.get(key)
        if exact_value:
            return exact_value

        # 2. Guard against Cache Stampede for L2/LLM calls
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        
        async with self._locks[key]:
            # Double-check L1 after acquiring lock
            exact_value = await self.exact_cache.get(key)
            if exact_value:
                return exact_value

            # 3. Attempt L2 Semantic Match
            if self.semantic_cache and prompt:
                semantic_value = await self.semantic_cache.get(prompt, tenant_id)
                if semantic_value:
                    logger.debug(f"L2 Semantic Hit for tenant {tenant_id}")
                    # Backfill L1 for faster subsequent exact matches
                    await self.exact_cache.set(key, semantic_value, self.default_ttl)
                    return semantic_value

        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None, prompt: Optional[str] = None, tenant_id: str = "default") -> None:
        """
        Store a value in both L1 and L2 caches.

        Args:
            key: The unique cache key for exact matches.
            value: The result to cache.
            ttl: Time-to-live in seconds.
            prompt: The original prompt for semantic indexing.
            tenant_id: The tenant associated with the request.
        """
        ttl = ttl or self.default_ttl
        await self._ensure_redis_connected()

        # Populate L1 Exact Cache
        await self.exact_cache.set(key, value, ttl)

        # Populate L2 Semantic Cache
        if self.semantic_cache and prompt:
            try:
                await self.semantic_cache.set(prompt, tenant_id, value, ttl)
            except Exception as e:
                logger.error(f"Failed to populate L2 Semantic cache: {e}")

    async def invalidate(self, key: str) -> None:
        """Remove a specific key from the L1 cache."""
        await self._ensure_redis_connected()
        await self.exact_cache.delete(key)

    async def invalidate_tenant(self, tenant_id: str) -> None:
        """Remove all semantic cache entries for a specific tenant."""
        if self.semantic_cache:
            await self.semantic_cache.invalidate_tenant(tenant_id)
