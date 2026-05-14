from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import os


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication."""

    def __init__(self, app, exclude_paths=None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or set()

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Simple mock validation
        api_key = auth_header.split(" ")[1]
        if not api_key.startswith("sk-"):
            raise HTTPException(status_code=401, detail="Invalid API Key")

        # Attach tenant_id to state
        request.state.tenant_id = "default"

        return await call_next(request)
