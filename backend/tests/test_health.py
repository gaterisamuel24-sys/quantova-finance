"""Tests for the health endpoint and environment-dependent app configuration."""

from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import SettingsFactory


def test_health_returns_ok(settings_factory: SettingsFactory) -> None:
    client = TestClient(create_app(settings_factory()))

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "quantova-api"
    assert body["environment"] == "test"


def test_docs_available_outside_production(settings_factory: SettingsFactory) -> None:
    client = TestClient(create_app(settings_factory(environment="development")))

    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_docs_disabled_in_production(settings_factory: SettingsFactory) -> None:
    client = TestClient(create_app(settings_factory(environment="production")))

    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    # The API itself must still work in production.
    assert client.get("/api/v1/health").status_code == 200
