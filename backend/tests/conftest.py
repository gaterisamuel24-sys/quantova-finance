"""Shared pytest fixtures."""

from collections.abc import Callable
from typing import Any

import pytest

from app.core.config import Settings

SettingsFactory = Callable[..., Settings]


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
