"""Response schemas for the health-check endpoints."""

from typing import Literal

from pydantic import BaseModel

CheckStatus = Literal["ok", "unavailable"]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    status: CheckStatus
    checks: dict[str, CheckStatus]
