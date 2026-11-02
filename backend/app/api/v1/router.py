"""Aggregates all v1 routers into a single router mounted under the API prefix."""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)
