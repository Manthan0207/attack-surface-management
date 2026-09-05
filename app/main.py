import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.assets import router as assets_router
from app.api.auth import router as auth_router
from app.api.domains import router as domains_router
from app.api.health import router as health_router
from app.api.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.bootstrap import seed_admin_user
from app.workers.discovery import recover_pending_jobs, start_workers, stop_workers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan hooks (startup / shutdown)."""
    db = SessionLocal()
    try:
        seed_admin_user(db)
    finally:
        db.close()

    if settings.testing:
        yield
        return

    start_workers()
    recover_pending_jobs()
    yield
    stop_workers()


def create_app() -> FastAPI:
    """Application factory for the Asset Discovery Service."""
    app = FastAPI(
        title="ASM Asset Discovery Service",
        description="SharkStriker Attack Surface Management — Asset Discovery Service",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(domains_router)
    app.include_router(assets_router)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
