from fastapi.middleware.cors import CORSMiddleware

def configure_cors(app):
    """Configure CORS for the FastAPI application."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
