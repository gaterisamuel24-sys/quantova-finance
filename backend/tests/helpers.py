"""Helpers shared by API tests."""

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

AUTH = "/api/v1/auth"
ORGS = "/api/v1/orgs"
PASSWORD = "a-strong-test-passphrase"


@dataclass(frozen=True)
class TestUser:
    __test__ = False  # tell pytest this is not a test class

    user_id: uuid.UUID
    email: str
    headers: dict[str, str]


def unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


def create_user(client: TestClient) -> TestUser:
    """Register and log in a fresh user; return their ID and Authorization header."""
    email = unique_email()
    registered = client.post(
        f"{AUTH}/register", json={"email": email, "password": PASSWORD, "full_name": "Test User"}
    )
    assert registered.status_code == 201, registered.text
    logged_in = client.post(f"{AUTH}/login", json={"email": email, "password": PASSWORD})
    assert logged_in.status_code == 200, logged_in.text
    return TestUser(
        user_id=uuid.UUID(registered.json()["id"]),
        email=email,
        headers={"Authorization": f"Bearer {logged_in.json()['access_token']}"},
    )


def run_query(database_url: str, sql: str, **params: Any) -> list[dict[str, Any]]:
    """Run a SQL query directly against a database, outside the app."""

    async def _run() -> list[dict[str, Any]]:
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(text(sql), params)
                return [dict(row) for row in result.mappings()]
        finally:
            await engine.dispose()

    return asyncio.run(_run())
