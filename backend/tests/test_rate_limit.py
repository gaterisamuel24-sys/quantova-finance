"""Rate limiting: limits are enforced, and the limiter fails open when Redis is down."""

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis

from app.core.rate_limit import LOGIN_PER_EMAIL, REGISTER_PER_IP, RateLimiter
from app.main import create_app
from tests.conftest import IntegrationUrls, SettingsFactory
from tests.helpers import AUTH, PASSWORD, unique_email

pytestmark = pytest.mark.integration


async def _flush_test_redis(redis_url: str) -> None:
    client = Redis.from_url(redis_url)
    try:
        await client.flushdb()
    finally:
        await client.aclose()


@pytest.fixture
def limited_client(
    settings_factory: SettingsFactory,
    integration_urls: IntegrationUrls,
    migrated_database: str,
) -> Iterator[TestClient]:
    """An app with rate limiting ON and empty counters (only the test Redis DB is flushed)."""
    asyncio.run(_flush_test_redis(integration_urls.redis_url))
    settings = settings_factory(
        database_url=integration_urls.database_url,
        redis_url=integration_urls.redis_url,
        rate_limit_enabled=True,
    )
    with TestClient(create_app(settings)) as client:
        yield client


def test_login_is_limited_per_email(limited_client: TestClient) -> None:
    email = unique_email()
    registered = limited_client.post(
        f"{AUTH}/register", json={"email": email, "password": PASSWORD, "full_name": "Target"}
    )
    assert registered.status_code == 201
    wrong = {"email": email, "password": "guessing-the-password"}

    for _ in range(LOGIN_PER_EMAIL.limit):
        assert limited_client.post(f"{AUTH}/login", json=wrong).status_code == 401

    blocked = limited_client.post(f"{AUTH}/login", json=wrong)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0

    # Even the correct password is refused until the window passes.
    correct = limited_client.post(f"{AUTH}/login", json={"email": email, "password": PASSWORD})
    assert correct.status_code == 429


def test_registration_is_limited_per_ip(limited_client: TestClient) -> None:
    def attempt() -> int:
        response = limited_client.post(
            f"{AUTH}/register",
            json={"email": unique_email(), "password": PASSWORD, "full_name": "Bot"},
        )
        return response.status_code

    assert [attempt() for _ in range(REGISTER_PER_IP.limit)] == [201] * REGISTER_PER_IP.limit
    assert attempt() == 429


@pytest.mark.anyio
async def test_limiter_fails_open_when_redis_is_unreachable() -> None:
    unreachable = Redis.from_url("redis://127.0.0.1:1/0")
    try:
        decision = await RateLimiter(unreachable).hit(LOGIN_PER_EMAIL, "someone")
    finally:
        await unreachable.aclose()

    assert decision.allowed is True


@pytest.mark.anyio
async def test_disabled_limiter_always_allows() -> None:
    decision = await RateLimiter(redis_client=None, enabled=False).hit(LOGIN_PER_EMAIL, "x")

    assert decision.allowed is True
