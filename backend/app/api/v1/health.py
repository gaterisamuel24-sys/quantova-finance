"""Health endpoints.

- GET /health        liveness: is the process up? Checks no dependencies.
- GET /health/ready  readiness: can the API serve real traffic? Checks PostgreSQL and Redis.
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.schemas.health import CheckStatus, HealthResponse, ReadinessResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

CHECK_TIMEOUT_SECONDS = 2.0


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service="quantova-api",
        version=settings.app_version,
        environment=settings.environment,
    )


async def _check_database(engine: AsyncEngine) -> CheckStatus:
    try:
        async with asyncio.timeout(CHECK_TIMEOUT_SECONDS):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Readiness: database check failed", exc_info=True)
        return "unavailable"
    return "ok"


async def _check_redis(redis_client: Any) -> CheckStatus:
    # Typed as Any: redis-py's async return types are too loose for strict mypy.
    try:
        async with asyncio.timeout(CHECK_TIMEOUT_SECONDS):
            await redis_client.ping()
    except Exception:
        logger.warning("Readiness: Redis check failed", exc_info=True)
        return "unavailable"
    return "ok"


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    database, redis = await asyncio.gather(
        _check_database(request.app.state.db_engine),
        _check_redis(request.app.state.redis),
    )
    checks: dict[str, CheckStatus] = {"database": database, "redis": redis}
    ready = all(value == "ok" for value in checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(status="ok" if ready else "unavailable", checks=checks)
