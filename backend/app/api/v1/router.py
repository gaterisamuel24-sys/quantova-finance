"""Aggregates all v1 routers into a single router mounted under the API prefix."""

from fastapi import APIRouter

from app.api.v1 import analytics, auth, health, imports, ledger, organizations

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(ledger.router)
api_router.include_router(imports.router)
api_router.include_router(analytics.router)
