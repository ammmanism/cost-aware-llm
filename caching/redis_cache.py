from typing import Optional, Any
import json

class RedisCache:
    """Mock Redis cache for testing purposes."""
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.cache = {}

    async def connect(self):
        print(f"Connecting to Redis at {self.redis_url}")

    async def get(self, key: str) -> Optional[Any]:
        return self.cache.get(key)

    async def set(self, key: str, value: Any, ttl: int):
        self.cache[key] = value

    async def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]
