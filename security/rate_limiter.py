import time
import os
import logging
import redis.asyncio as redis
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Elite Tier Rate Limiter utilizing Redis Lua Scripts for atomic 
    Token Bucket operations ensuring zero race-conditions during burst traffic.
    """
    
    # Lua script for atomic Token Bucket rate limiting
    LUA_SCRIPT = """
    local key = KEYS[1]
    local max_tokens = tonumber(ARGV[1])
    local refill_rate = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    local requested = 1
    
    local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
    local tokens = tonumber(bucket[1]) or max_tokens
    local last_refill = tonumber(bucket[2]) or now
    
    local elapsed_time = math.max(0, now - last_refill)
    local refilled_tokens = elapsed_time * refill_rate
    tokens = math.min(max_tokens, tokens + refilled_tokens)
    
    if tokens >= requested then
        tokens = tokens - requested
        redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
        redis.call('EXPIRE', key, math.ceil(max_tokens / refill_rate) * 2)
        return {1, tokens}
    else:
        return {0, tokens}
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.refill_rate = max_requests / window_seconds
        self.redis_url = os.environ.get("REDIS_URL")
        self._redis: Optional[redis.Redis] = None
        self._connected = False
        
        # Fallback dictionary for local dev
        self.requests: Dict[str, list] = {}

    async def _ensure_redis_connected(self):
        if self.redis_url and not self._connected:
            try:
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                await self._redis.ping()
                self._connected = True
                logger.info("Elite RateLimiter connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect Redis for RateLimiter: {e}")
                self.redis_url = None

    async def is_allowed(self, tenant_id: str) -> Tuple[bool, int]:
        await self._ensure_redis_connected()
        now = time.time()
        
        if self._redis:
            # Execute atomic Lua script
            key = f"ratelimit:{tenant_id}"
            result = await self._redis.eval(
                self.LUA_SCRIPT, 1, key, 
                self.max_requests, self.refill_rate, now
            )
            allow = bool(result[0])
            remaining = int(result[1])
            return allow, remaining
        else:
            # Fallback to in-memory sliding window
            if tenant_id not in self.requests:
                self.requests[tenant_id] = []
            
            self.requests[tenant_id] = [req for req in self.requests[tenant_id] if now - req < self.window_seconds]
            
            if len(self.requests[tenant_id]) < self.max_requests:
                self.requests[tenant_id].append(now)
                return True, self.max_requests - len(self.requests[tenant_id])
            
            return False, 0
