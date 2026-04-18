import os
import logging
from typing import Dict, Optional, Tuple
import redis.asyncio as redis
import hashlib
import secrets

logger = logging.getLogger(__name__)

class KeyManager:
    """
    Manage tenant API keys with Redis persistence.
    """

    def __init__(self):
        self.redis_url = os.environ.get("REDIS_URL")
        self._redis: Optional[redis.Redis] = None
        self._connected = False

    async def _ensure_redis_connected(self):
        if self.redis_url and not self._connected:
            try:
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                await self._redis.ping()
                self._connected = True
                logger.info("KeyManager connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect Redis for KeyManager: {e}")
                self.redis_url = None

    async def validate_key(self, api_key: str) -> Optional[str]:
        """Return tenant_id if key is valid, else None."""
        await self._ensure_redis_connected()
        if self._redis:
            tenant_id = await self._redis.get(f"apikey:{self._hash_key(api_key)}")
            return tenant_id
        else:
            # Fallback to in-memory (from environment)
            # This is handled by the auth middleware directly
            return None

    async def create_key(self, tenant_id: str, prefix: str = "sk") -> str:
        """Generate and store a new API key for a tenant."""
        await self._ensure_redis_connected()
        raw_key = f"{prefix}-{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)

        if self._redis:
            await self._redis.set(f"apikey:{key_hash}", tenant_id)
            # Also store in a set for this tenant
            await self._redis.sadd(f"tenant:{tenant_id}:keys", key_hash)
            logger.info(f"Created API key for tenant {tenant_id}")
        return raw_key

    async def revoke_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        await self._ensure_redis_connected()
        key_hash = self._hash_key(api_key)
        if self._redis:
            tenant_id = await self._redis.get(f"apikey:{key_hash}")
            if tenant_id:
                await self._redis.delete(f"apikey:{key_hash}")
                await self._redis.srem(f"tenant:{tenant_id}:keys", key_hash)
                return True
        return False

    async def list_tenant_keys(self, tenant_id: str) -> list:
        """List key hashes for a tenant (not the actual keys)."""
        await self._ensure_redis_connected()
        if self._redis:
            return await self._redis.smembers(f"tenant:{tenant_id}:keys")
        return []

    def _hash_key(self, key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()
