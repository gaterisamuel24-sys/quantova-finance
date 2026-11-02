"""Tests for configuration safety: required values, secret masking, template accuracy."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from tests.conftest import SettingsFactory

ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"


def test_missing_required_settings_fail_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DATABASE_URL", "REDIS_URL", "JWT_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    missing = {error["loc"][0] for error in exc_info.value.errors()}
    assert {"database_url", "redis_url", "jwt_secret_key"} <= missing


def test_short_jwt_secret_is_rejected(settings_factory: SettingsFactory) -> None:
    with pytest.raises(ValidationError, match="at least 32 characters"):
        settings_factory(jwt_secret_key="too-short")


def test_secrets_are_masked(settings_factory: SettingsFactory) -> None:
    settings = settings_factory(
        database_url="postgresql+asyncpg://user:supersecret@db.example.com/app",
        redis_url="redis://:alsosecret@cache.example.com:6379/0",
    )

    for leaked_view in (repr(settings), str(settings), str(settings.model_dump())):
        assert "supersecret" not in leaked_view
        assert "alsosecret" not in leaked_view
        assert settings.jwt_secret_key.get_secret_value() not in leaked_view

    # The real value is still available when explicitly requested.
    assert "supersecret" in settings.database_url.get_secret_value()


def test_env_example_documents_every_required_setting() -> None:
    documented = {
        line.split("=", 1)[0].strip()
        for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "=" in line
    }
    required = {
        name.upper() for name, field in Settings.model_fields.items() if field.is_required()
    }

    assert required <= documented, f"Missing from .env.example: {required - documented}"
