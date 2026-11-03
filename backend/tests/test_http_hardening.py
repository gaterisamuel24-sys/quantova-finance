"""Security headers, request ids, the catch-all error handler and the request size limit.

These need no database: they exercise the HTTP layer around the routes.
"""

import re
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import MAX_REQUEST_BYTES, create_app
from tests.conftest import SettingsFactory

HEALTH = "/api/v1/health"


@pytest.fixture
def app(settings_factory: SettingsFactory) -> FastAPI:
    return create_app(settings_factory(cors_origins=["http://localhost:5173"]))


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_every_response_carries_security_headers(client: TestClient) -> None:
    headers = client.get(HEALTH).headers

    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert headers["cache-control"] == "no-store"
    assert "camera=()" in headers["permissions-policy"]
    assert "strict-transport-security" not in headers  # local development runs over http


def test_hsts_is_sent_in_production(settings_factory: SettingsFactory) -> None:
    with TestClient(create_app(settings_factory(environment="production"))) as client:
        headers = client.get(HEALTH).headers

    assert headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


def test_cors_preflight_responses_are_hardened_too(client: TestClient) -> None:
    response = client.options(
        HEALTH,
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_requests_get_an_id(client: TestClient) -> None:
    generated = client.get(HEALTH).headers["x-request-id"]
    kept = client.get(HEALTH, headers={"X-Request-ID": "trace-12345678"}).headers["x-request-id"]
    unsafe = client.get(HEALTH, headers={"X-Request-ID": "<script>alert(1)</script>"})

    assert re.fullmatch(r"[0-9a-f]{32}", generated)
    assert kept == "trace-12345678"
    assert re.fullmatch(r"[0-9a-f]{32}", unsafe.headers["x-request-id"])


def test_unexpected_errors_reveal_nothing(app: FastAPI, client: TestClient) -> None:
    async def boom() -> None:
        raise RuntimeError("database password is hunter2 at /srv/secret/config.py")

    app.add_api_route("/boom", boom)

    response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "Something went wrong on our side. Please try again."
    assert body["request_id"] == response.headers["x-request-id"]
    assert "hunter2" not in response.text
    assert "RuntimeError" not in response.text


def test_oversized_requests_are_refused_before_reading(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        content=b"x" * (MAX_REQUEST_BYTES + 1),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.headers["x-content-type-options"] == "nosniff"
