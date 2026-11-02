"""Shared pytest fixtures."""

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from app.core.config import Settings

SettingsFactory = Callable[..., Settings]


class IntegrationEnvironment(BaseSettings):
    """Connection details for the dedicated test services, from env vars or backend/.env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    test_database_url: SecretStr | None = None
    test_redis_url: SecretStr | None = None


@pytest.fixture
def settings_factory() -> SettingsFactory:
    """Build Settings for tests without reading backend/.env.

    Tests must not depend on a developer's local .env (it doesn't exist in CI),
    so every value is explicit. Pass keyword overrides to change any field.
    """

    def factory(**overrides: Any) -> Settings:
        values: dict[str, Any] = {
            "environment": "test",
            "database_url": "postgresql+asyncpg://test:test@127.0.0.1:5432/test",
            "redis_url": "redis://:test@127.0.0.1:6379/0",
        }
        values.update(overrides)
        return Settings(_env_file=None, **values)

    return factory


@pytest.fixture
def integration_settings(settings_factory: SettingsFactory) -> Settings:
    """Settings pointing at the real test database and Redis.

    Fails loudly if they are not configured, and refuses any database whose name
    does not end in "_test", so the suite can never run against development data.
    """
    env = IntegrationEnvironment()
    if env.test_database_url is None or env.test_redis_url is None:
        pytest.fail(
            "Integration tests need TEST_DATABASE_URL and TEST_REDIS_URL "
            "(see backend/.env.example)."
        )

    database_url = env.test_database_url.get_secret_value()
    database_name = make_url(database_url).database or ""
    if not database_name.endswith("_test"):
        pytest.fail(
            f"Refusing to run: test database name must end in '_test' (got '{database_name}')."
        )

    return settings_factory(
        database_url=database_url,
        redis_url=env.test_redis_url.get_secret_value(),
    )
