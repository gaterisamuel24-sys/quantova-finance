"""Shared pytest fixtures."""

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import Settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
SettingsFactory = Callable[..., Settings]

# Obviously fake, 68 characters: passes the length check, never mistaken for a real key.
TEST_JWT_SECRET = "test-" + "0123456789abcdef" * 4


class IntegrationEnvironment(BaseSettings):
    """Connection details for the dedicated test services, from env vars or backend/.env."""

    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    test_database_url: SecretStr | None = None
    test_redis_url: SecretStr | None = None


@dataclass(frozen=True)
class IntegrationUrls:
    database_url: str
    redis_url: str


def make_alembic_config(database_url: str) -> Config:
    """Alembic configuration pointed at an explicit database (never the app's DATABASE_URL)."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.attributes["database_url"] = database_url
    return config


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Run async tests on asyncio (the event loop FastAPI and asyncpg use)."""
    return "asyncio"


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
            "jwt_secret_key": TEST_JWT_SECRET,
            "enforce_member_limits": False,
            "rate_limit_enabled": False,
        }
        if overrides.get("environment") == "production":
            # Production settings must pass the safety checks in app/core/config.py.
            values.update(
                {"rate_limit_enabled": True, "enforce_member_limits": True, "cors_origins": []}
            )
        values.update(overrides)
        return Settings(_env_file=None, **values)

    return factory


@pytest.fixture(scope="session")
def integration_urls() -> IntegrationUrls:
    """Test service URLs. Fails loudly if missing; refuses databases not named *_test."""
    env = IntegrationEnvironment(_env_file=BACKEND_DIR / ".env")
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

    return IntegrationUrls(
        database_url=database_url,
        redis_url=env.test_redis_url.get_secret_value(),
    )


@pytest.fixture(scope="session")
def migrated_database(integration_urls: IntegrationUrls) -> str:
    """Rebuild the test schema from nothing by running every migration. Once per test run."""
    url = integration_urls.database_url

    async def reset_schema() -> None:
        engine = create_async_engine(url)
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA public CASCADE"))
            await connection.execute(text("CREATE SCHEMA public"))
        await engine.dispose()

    asyncio.run(reset_schema())
    command.upgrade(make_alembic_config(url), "head")
    return url


@pytest.fixture
def integration_settings(
    settings_factory: SettingsFactory, integration_urls: IntegrationUrls
) -> Settings:
    """App settings pointing at the real test database and Redis."""
    return settings_factory(
        database_url=integration_urls.database_url,
        redis_url=integration_urls.redis_url,
    )


@pytest.fixture
async def db_session(migrated_database: str) -> AsyncIterator[AsyncSession]:
    """A session inside a transaction that is always rolled back.

    Each test sees a clean database and leaves nothing behind, without the cost
    of recreating tables. Even session.commit() inside a test only commits a
    savepoint within this outer transaction.
    """
    engine = create_async_engine(migrated_database)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()
