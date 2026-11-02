"""End-to-end tests for the authentication API against the real test database."""

import asyncio
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.v1.auth import REFRESH_COOKIE_NAME
from app.core.config import Settings
from app.main import create_app

pytestmark = pytest.mark.integration

AUTH = "/api/v1/auth"
PASSWORD = "a-strong-test-passphrase"
QueryDb = Callable[..., list[dict[str, Any]]]


# ── Fixtures and helpers ──────────────────────────────


@pytest.fixture
def client(integration_settings: Settings, migrated_database: str) -> Iterator[TestClient]:
    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


@pytest.fixture
def query_db(migrated_database: str) -> QueryDb:
    """Run a SQL query directly against the test database, outside the app."""

    def run(sql: str, **params: Any) -> list[dict[str, Any]]:
        async def _run() -> list[dict[str, Any]]:
            engine = create_async_engine(migrated_database)
            try:
                async with engine.connect() as connection:
                    result = await connection.execute(text(sql), params)
                    return [dict(row) for row in result.mappings()]
            finally:
                await engine.dispose()

        return asyncio.run(_run())

    return run


def unique_email() -> str:
    # Each test uses fresh accounts, so tests never interfere with each other.
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


def register(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, Any]:
    response = client.post(
        f"{AUTH}/register", json={"email": email, "password": password, "full_name": "Test User"}
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def login(client: TestClient, email: str, password: str = PASSWORD) -> str:
    response = client.post(f"{AUTH}/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


def use_refresh_cookie(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE_NAME, token)


# ── Registration ──────────────────────────────────────


def test_register_creates_user_and_hides_password_hash(
    client: TestClient, query_db: QueryDb
) -> None:
    email = unique_email()

    body = register(client, email)

    assert body["email"] == email
    assert body["platform_role"] == "user"
    assert "password" not in str(body).lower()
    stored = query_db("SELECT password_hash FROM users WHERE email = :email", email=email)
    assert stored[0]["password_hash"].startswith("$argon2id$")


def test_register_normalizes_email(client: TestClient) -> None:
    local_part = f"Mixed-{uuid.uuid4().hex[:8]}"

    body = register(client, f"  {local_part}@Example.COM ")

    assert body["email"] == f"{local_part.lower()}@example.com"


def test_register_rejects_duplicate_email_case_insensitively(client: TestClient) -> None:
    email = unique_email()
    register(client, email)

    response = client.post(
        f"{AUTH}/register",
        json={"email": email.upper(), "password": PASSWORD, "full_name": "Copycat"},
    )

    assert response.status_code == 409


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        f"{AUTH}/register",
        json={"email": unique_email(), "password": "short", "full_name": "Test User"},
    )

    assert response.status_code == 422


def test_register_rejects_unknown_fields(client: TestClient) -> None:
    # Mass-assignment attempt: clients must not be able to set their own role.
    response = client.post(
        f"{AUTH}/register",
        json={
            "email": unique_email(),
            "password": PASSWORD,
            "full_name": "Sneaky",
            "platform_role": "superadmin",
        },
    )

    assert response.status_code == 422


# ── Login and current user ────────────────────────────


def test_login_returns_access_token_and_protected_refresh_cookie(client: TestClient) -> None:
    email = unique_email()
    register(client, email)

    response = client.post(f"{AUTH}/login", json={"email": email, "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60
    cookie_header = response.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "samesite=strict" in cookie_header
    assert "path=/api/v1/auth" in cookie_header
    assert client.cookies.get(REFRESH_COOKIE_NAME)


def test_login_failures_are_indistinguishable(client: TestClient) -> None:
    email = unique_email()
    register(client, email)

    wrong_password = client.post(
        f"{AUTH}/login", json={"email": email, "password": "not-the-right-password"}
    )
    unknown_email = client.post(
        f"{AUTH}/login", json={"email": unique_email(), "password": PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_me_requires_a_valid_access_token(client: TestClient) -> None:
    email = unique_email()
    register(client, email)

    assert client.get(f"{AUTH}/me").status_code == 401
    garbage = client.get(f"{AUTH}/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert garbage.status_code == 401

    token = login(client, email)
    response = client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == email


# ── Refresh, reuse detection and logout ───────────────


def test_refresh_rotates_the_refresh_token(client: TestClient) -> None:
    email = unique_email()
    register(client, email)
    login(client, email)
    first_refresh_token = client.cookies.get(REFRESH_COOKIE_NAME)

    response = client.post(f"{AUTH}/refresh")

    assert response.status_code == 200
    assert response.json()["access_token"]
    second_refresh_token = client.cookies.get(REFRESH_COOKIE_NAME)
    assert second_refresh_token and second_refresh_token != first_refresh_token


def test_reused_refresh_token_revokes_the_whole_session(
    client: TestClient, query_db: QueryDb
) -> None:
    email = unique_email()
    user_id = uuid.UUID(register(client, email)["id"])
    login(client, email)
    stolen_copy = client.cookies.get(REFRESH_COOKIE_NAME)
    assert stolen_copy is not None
    assert client.post(f"{AUTH}/refresh").status_code == 200
    legitimate_token = client.cookies.get(REFRESH_COOKIE_NAME)
    assert legitimate_token is not None

    # The attacker replays the old token: rejected, and the session family is revoked.
    use_refresh_cookie(client, stolen_copy)
    assert client.post(f"{AUTH}/refresh").status_code == 401

    # The legitimate user's newer token no longer works either.
    use_refresh_cookie(client, legitimate_token)
    assert client.post(f"{AUTH}/refresh").status_code == 401

    events = query_db(
        "SELECT action FROM audit_logs WHERE actor_user_id = :user_id", user_id=user_id
    )
    assert "auth.refresh_token_reuse_detected" in {event["action"] for event in events}


def test_logout_ends_the_session(client: TestClient) -> None:
    email = unique_email()
    register(client, email)
    login(client, email)
    refresh_token = client.cookies.get(REFRESH_COOKIE_NAME)
    assert refresh_token is not None

    assert client.post(f"{AUTH}/logout").status_code == 204

    use_refresh_cookie(client, refresh_token)
    assert client.post(f"{AUTH}/refresh").status_code == 401


def test_authentication_events_are_audited(client: TestClient, query_db: QueryDb) -> None:
    email = unique_email()
    user_id = uuid.UUID(register(client, email)["id"])
    client.post(f"{AUTH}/login", json={"email": email, "password": "not-the-right-password"})
    login(client, email)

    events = query_db(
        "SELECT action FROM audit_logs WHERE actor_user_id = :user_id", user_id=user_id
    )

    assert {"user.registered", "auth.login_failed", "auth.login_succeeded"} <= {
        event["action"] for event in events
    }
