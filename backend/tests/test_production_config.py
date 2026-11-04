"""Production refuses unsafe settings, and logs are structured JSON lines."""

import json
import logging
import sys
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import configuration_problems, configuration_warnings
from app.core.http_hardening import request_id_var
from app.core.logging import JsonFormatter, configure_logging
from app.db.session import create_engine
from app.main import create_app
from tests.conftest import SettingsFactory

BILLING = {
    "stripe_secret_key": "sk_test_not_real",
    "stripe_price_pro": "price_pro",
    "stripe_price_business": "price_business",
}


@pytest.fixture(autouse=True)
def no_render_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.delenv("APP_BASE_URL", raising=False)


def test_safe_production_settings_start(settings_factory: SettingsFactory) -> None:
    settings = settings_factory(environment="production")

    assert configuration_problems(settings) == []
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/health").status_code == 200


@pytest.mark.parametrize(
    ("overrides", "setting"),
    [
        ({"rate_limit_enabled": False}, "RATE_LIMIT_ENABLED"),
        ({"enforce_member_limits": False}, "ENFORCE_MEMBER_LIMITS"),
        ({"cors_origins": ["*"]}, "CORS_ORIGINS"),
        ({"cors_origins": ["http://quantova.example"]}, "CORS_ORIGINS"),
        ({**BILLING, "app_base_url": "http://quantova.example"}, "APP_BASE_URL"),
    ],
)
def test_unsafe_production_settings_are_refused(
    settings_factory: SettingsFactory, overrides: dict[str, object], setting: str
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        settings_factory(environment="production", **overrides)

    assert setting in str(exc_info.value)


def test_billing_in_production_needs_an_https_return_address(
    settings_factory: SettingsFactory,
) -> None:
    settings = settings_factory(
        environment="production", app_base_url="https://quantova.example", **BILLING
    )

    assert settings.billing_enabled


def test_live_stripe_keys_only_work_in_production(settings_factory: SettingsFactory) -> None:
    live = {**BILLING, "stripe_secret_key": "sk_live_not_real"}

    for environment in ("development", "test", "staging"):
        with pytest.raises(ValidationError, match="STRIPE_SECRET_KEY is a live key"):
            settings_factory(environment=environment, **live)
    with pytest.raises(ValidationError, match="live key"):
        settings_factory(stripe_secret_key="rk_live_not_real")  # restricted keys too

    production = settings_factory(
        environment="production", app_base_url="https://quantova.example", **live
    )
    assert production.billing_enabled


def test_errors_name_the_setting_but_never_show_values(
    settings_factory: SettingsFactory,
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        settings_factory(
            environment="production",
            rate_limit_enabled=False,
            database_url="postgresql+asyncpg://quantova:pw-must-not-leak@db.internal/quantova",
        )

    message = str(exc_info.value)
    assert "RATE_LIMIT_ENABLED" in message
    assert "pw-must-not-leak" not in message


def test_production_warnings(settings_factory: SettingsFactory) -> None:
    settings = settings_factory(
        environment="production", app_base_url="https://quantova.example", **BILLING
    )

    warnings = configuration_warnings(settings)

    assert any("test mode" in warning for warning in warnings)
    assert any("STRIPE_WEBHOOK_SECRET" in warning for warning in warnings)
    assert any("OPENAI_API_KEY" in warning for warning in warnings)
    assert configuration_warnings(settings_factory(**BILLING)) == []  # only in production


def test_startup_logs_the_warnings(
    settings_factory: SettingsFactory, caplog: pytest.LogCaptureFixture
) -> None:
    settings = settings_factory(
        environment="production", app_base_url="https://quantova.example", **BILLING
    )

    with caplog.at_level(logging.WARNING, logger="app.startup"):
        create_app(settings)

    assert "Stripe is in test mode: no real payments are taken" in caplog.messages


def test_database_errors_hide_query_values_outside_development(
    settings_factory: SettingsFactory,
) -> None:
    assert create_engine(settings_factory(environment="production")).sync_engine.hide_parameters
    assert not create_engine(settings_factory()).sync_engine.hide_parameters


def _record(message: str, *args: object, exc_info: bool = False) -> logging.LogRecord:
    error_info = None
    if exc_info:
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            error_info = sys.exc_info()
    return logging.LogRecord("app.test", logging.ERROR, __file__, 1, message, args, error_info)


def test_log_lines_are_json_with_the_request_id() -> None:
    token = request_id_var.set("req-12345678")
    try:
        line = JsonFormatter().format(_record("Imported %d rows", 12))
    finally:
        request_id_var.reset(token)

    entry = json.loads(line)
    assert entry["message"] == "Imported 12 rows"
    assert entry["level"] == "ERROR"
    assert entry["logger"] == "app.test"
    assert entry["request_id"] == "req-12345678"
    assert entry["time"].endswith("+00:00")


def test_a_log_message_can_never_forge_a_second_line() -> None:
    line = JsonFormatter().format(_record("bad input: %s", 'x\n{"level": "INFO"}'))

    assert "\n" not in line
    assert json.loads(line)["message"] == 'bad input: x\n{"level": "INFO"}'


def test_exceptions_are_kept_in_one_entry() -> None:
    line = JsonFormatter().format(_record("Unhandled error", exc_info=True))

    entry = json.loads(line)
    assert "RuntimeError: boom" in entry["exception"]
    assert "\n" not in line


@pytest.fixture
def restore_logging() -> Iterator[None]:
    names = ("", "uvicorn", "uvicorn.error", "uvicorn.access")
    saved = {
        name: (
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).level,
            logging.getLogger(name).propagate,
        )
        for name in names
    }
    yield
    for name, (handlers, level, propagate) in saved.items():
        target = logging.getLogger(name)
        target.handlers = handlers
        target.setLevel(level)
        target.propagate = propagate


@pytest.mark.usefixtures("restore_logging")
def test_json_logging_is_only_switched_on_when_asked(settings_factory: SettingsFactory) -> None:
    before = list(logging.getLogger().handlers)
    configure_logging(settings_factory())  # LOG_FORMAT defaults to text
    assert logging.getLogger().handlers == before

    configure_logging(settings_factory(log_format="json", log_level="WARNING"))
    configure_logging(settings_factory(log_format="json", log_level="WARNING"))  # repeatable

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JsonFormatter)
    assert root.level == logging.WARNING
    assert logging.getLogger("uvicorn.access").propagate
    assert logging.getLogger("uvicorn.access").handlers == []
