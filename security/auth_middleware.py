from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional, Set
import os
import logging

logger = logging.getLogger(__name__)

class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    API Key authentication middleware.
    Validates Bearer tokens and attaches tenant_id to request state.
    """

    def __init__(self, app, exclude_paths: Set[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or {"/health", "/metrics", "/docs", "/openapi.json", "/redoc", "/admin"}
        # In production, this should be loaded from a secure database or Redis
        # For demonstration, we load from environment or use a default map
        self._load_keys()

    def _load_keys(self):
        """Load API keys from environment or config."""
        self.tenant_keys: Dict[str, str] = {}
        # Format: API_KEYS=tenant1:sk-key1,tenant2:sk-key2
        keys_env = os.environ.get("API_KEYS", "")
        if keys_env:
            for pair in keys_env.split(","):
                if ":" in pair:
                    tenant, key = pair.split(":", 1)
                    self.tenant_keys[key.strip()] = tenant.strip()
        else:
            # Default test keys (NEVER use in production)
            self.tenant_keys = {
                "sk-test-123": "tenant_alpha",
                "sk-test-456": "tenant_beta",
            }
            logger.warning("Using default test API keys. Set API_KEYS environment variable for production.")

    async def dispatch(self, request: Request, call_next):
        # Skip auth for excluded paths
        if request.url.path in self.exclude_paths or request.url.path.startswith("/admin"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid Authorization header format. Use 'Bearer <token>'")

        api_key = auth_header[7:].strip()
        if not api_key:
            raise HTTPException(status_code=401, detail="Empty API key")

        tenant_id = self.tenant_keys.get(api_key)
        if not tenant_id:
            logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Attach tenant_id to request state for downstream use
        request.state.tenant_id = tenant_id
        request.state.api_key_id = api_key[:8]  # For logging, not full key

        return await call_next(request)
