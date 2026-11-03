"""Aggregates all v1 routers into a single router mounted under the API prefix."""

from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    auth,
    billing,
    health,
    imports,
    insights,
    ledger,
    organizations,
    reports,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(ledger.router)
api_router.include_router(imports.router)
api_router.include_router(analytics.router)
api_router.include_router(reports.router)
api_router.include_router(insights.router)
api_router.include_router(billing.router)
