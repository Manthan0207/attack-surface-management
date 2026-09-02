from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    """Application factory for the Asset Discovery Service."""
    app = FastAPI(
        title="ASM Asset Discovery Service",
        version="0.1.0",
        debug=settings.debug,
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
