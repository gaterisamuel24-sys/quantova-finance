"""FastAPI application factory.

Run in development with:
    uv run uvicorn app.main:create_app --factory --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.core.http_hardening import (
    BodySizeLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)
from app.db.session import create_engine, create_sessionmaker

# The largest legitimate request is a 5 MB CSV import; allow some room for the form encoding.
MAX_REQUEST_BYTES = 6 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create shared connection pools at startup and close them at shutdown."""
    settings: Settings = app.state.settings

    engine = create_engine(settings)
    redis_client = Redis.from_url(settings.redis_url.get_secret_value(), decode_responses=True)

    app.state.db_engine = engine
    app.state.db_sessionmaker = create_sessionmaker(engine)
    app.state.redis = redis_client
    try:
        yield
    finally:
        await redis_client.aclose()
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure a FastAPI application instance."""
    settings = settings or get_settings()
    is_production = settings.environment == "production"

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        # Interactive API docs are useful in development but expose the
        # full API surface, so they are disabled in production.
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
    )
    app.state.settings = settings

    # Middleware runs outermost-first in the reverse order of these calls: the request id is
    # assigned first, then the size check, then CORS, and security headers wrap every
    # response, including CORS preflights and size rejections.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=MAX_REQUEST_BYTES)
    app.add_middleware(
        SecurityHeadersMiddleware, hsts=settings.environment in ("staging", "production")
    )
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app
