"""Liveness endpoint used by monitoring, load balancers and Docker health checks."""

from fastapi import APIRouter, Request

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service="quantova-api",
        version=settings.app_version,
        environment=settings.environment,
    )
