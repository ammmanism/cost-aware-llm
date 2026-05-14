import asyncio
import time
from typing import Any, Dict, Optional


class ExactCache:
    """
    In-memory L1 cache for exact string matching.

    Provides high-speed caching for environments where Redis is not available.
    Supports time-to-live (TTL) and thread-safe operations.
    """

    def __init__(self):
        # key -> (value, expiry_timestamp)
        self._cache: Dict[str, tuple[Any, Optional[float]]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache if it hasn't expired.

        Returns:
            The cached value, or None if missing/expired.
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if expiry and time.time() > expiry:
                del self._cache[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value in the cache with an optional TTL.
        """
        async with self._lock:
            expiry = time.time() + ttl if ttl else None
            self._cache[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        """
        Remove a value from the cache manually.
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

    async def clear(self) -> None:
        """
        Remove all entries from the cache.
        """
        async with self._lock:
            self._cache.clear()
