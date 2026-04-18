from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os

def configure_cors(app, allowed_origins: List[str] = None):
    """
    Configure CORS for the FastAPI app.
    In production, allowed_origins should be specific domains.
    """
    if allowed_origins is None:
        # Load from environment or use restrictive default
        origins_env = os.environ.get("ALLOWED_ORIGINS", "")
        if origins_env:
            allowed_origins = [o.strip() for o in origins_env.split(",")]
        else:
            allowed_origins = []  # Empty means no CORS (block all cross-origin requests)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    return app
