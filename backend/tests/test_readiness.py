"""Tests for the readiness endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import SettingsFactory


def test_readiness_reports_unreachable_services(settings_factory: SettingsFactory) -> None:
    # Port 1 has nothing listening, so both checks must fail quickly and safely.
    settings = settings_factory(
        database_url="postgresql+asyncpg://nobody:nothing@127.0.0.1:1/none_test",
        redis_url="redis://127.0.0.1:1/0",
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    # Exact body: proves no internal error details leak to the caller.
    assert response.json() == {
        "status": "unavailable",
        "checks": {"database": "unavailable", "redis": "unavailable"},
    }


@pytest.mark.integration
def test_readiness_ok_with_real_services(integration_settings: Settings) -> None:
    with TestClient(create_app(integration_settings)) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}
