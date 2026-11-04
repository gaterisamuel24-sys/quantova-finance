"""Application settings, loaded from environment variables (and .env in development)."""

import os
from functools import lru_cache
from typing import Any, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET_LENGTH = 32
ASYNC_DRIVER_SCHEME = "postgresql+asyncpg://"
# Stripe secret keys (sk_) and restricted keys (rk_) say whether they move real money.
LIVE_STRIPE_KEY_PREFIXES = ("sk_live_", "rk_live_")
TEST_STRIPE_KEY_PREFIXES = ("sk_test_", "rk_test_")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # A rejected setting is never echoed back: the error names it but omits its value,
        # so a mistyped secret cannot end up in the platform's logs.
        hide_input_in_errors=True,
    )

    # ── Application ────────────────────────────────────
    app_name: str = "Quantova Finance API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173"]

    # ── Infrastructure (required, no defaults) ─────────
    # SecretStr masks the value as '**********' in repr(), logs and error messages.
    # Read the real value explicitly with .get_secret_value().
    database_url: SecretStr
    redis_url: SecretStr

    # ── Authentication ─────────────────────────────────
    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "quantova-api"
    jwt_audience: str = "quantova-app"
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_ttl_days: int = Field(default=14, ge=1, le=90)

    # ── Abuse protection ───────────────────────────────
    rate_limit_enabled: bool = True

    # ── Plan limits ────────────────────────────────────
    # Members per organization follow the plan (Free 1, Pro 5, Business 25). Only the test
    # suite turns this off, so tests that need several members don't each need a paid plan.
    enforce_member_limits: bool = True

    # ── AI insights (optional) ─────────────────────────
    # Without OPENAI_API_KEY the AI features are switched off; everything else works.
    openai_api_key: SecretStr | None = None
    openai_model: str = Field(default="gpt-5.4-mini", min_length=1, max_length=100)
    ai_request_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    ai_max_output_tokens: int = Field(default=1500, ge=200, le=8000)
    # Server-wide safety cap on AI insights per organization per day. The plan's own
    # allowance applies below it (Free 3, Pro 20, Business 100).
    ai_daily_insights_per_org: int = Field(default=100, ge=1, le=1000)

    # ── Billing (optional) ─────────────────────────────
    # Without STRIPE_SECRET_KEY and both price ids, upgrading is switched off.
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_price_pro: str | None = Field(default=None, max_length=255)
    stripe_price_business: str | None = Field(default=None, max_length=255)
    # Where the browser returns after Stripe Checkout or the billing portal.
    app_base_url: str = "http://localhost:5173"

    # ── Frontend ───────────────────────────────────────
    # In production the API also serves the built frontend from this folder (set in the
    # Docker image), so the app and the API share one origin. Unset in development.
    frontend_dist_dir: str | None = None

    # ── Logging ────────────────────────────────────────
    # "json" (set in the Docker image) writes one JSON object per line, which the hosting
    # platform's log search can filter by level or request id. "text" suits a terminal.
    log_format: Literal["text", "json"] = "text"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @property
    def ai_enabled(self) -> bool:
        return self.openai_api_key is not None

    @property
    def billing_enabled(self) -> bool:
        return (
            self.stripe_secret_key is not None
            and self.stripe_price_pro is not None
            and self.stripe_price_business is not None
        )

    @field_validator(
        "openai_api_key",
        "stripe_secret_key",
        "stripe_webhook_secret",
        "stripe_price_pro",
        "stripe_price_business",
        mode="before",
    )
    @classmethod
    def blank_means_not_set(cls, value: object) -> object:
        # "OPENAI_API_KEY=" in .env (an empty value) must switch a feature off, not send "".
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value

    @field_validator("app_base_url")
    @classmethod
    def base_url_without_trailing_slash(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("APP_BASE_URL must start with http:// or https://")
        return value.rstrip("/")

    @field_validator("database_url", mode="before")
    @classmethod
    def use_the_async_driver(cls, value: object) -> object:
        """Hosting platforms give plain postgres:// URLs; the app needs the asyncpg driver."""
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        if isinstance(raw, str):
            for scheme in ("postgres://", "postgresql://"):
                if raw.startswith(scheme):
                    return ASYNC_DRIVER_SCHEME + raw.removeprefix(scheme)
        return value

    @model_validator(mode="before")
    @classmethod
    def default_base_url_from_render(cls, data: Any) -> Any:
        """On Render, use the service's public address unless APP_BASE_URL is set."""
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        if isinstance(data, dict) and render_url and not data.get("app_base_url"):
            return {**data, "app_base_url": render_url}
        return data

    @field_validator("jwt_secret_key")
    @classmethod
    def jwt_secret_must_be_strong(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET_KEY must be at least {MIN_JWT_SECRET_LENGTH} characters; "
                "generate 64 random hex characters (see backend/.env.example)"
            )
        return value

    @model_validator(mode="after")
    def refuse_unsafe_configuration(self) -> Self:
        """Fail at startup, before serving anyone, if the configuration is unsafe."""
        problems = configuration_problems(self)
        if problems:
            raise ValueError("Unsafe configuration: " + "; ".join(problems))
        return self


def _stripe_key(settings: Settings) -> str:
    key = settings.stripe_secret_key
    return key.get_secret_value() if key is not None else ""


def configuration_problems(settings: Settings) -> list[str]:
    """Settings that must never go live. Messages name the setting, never its value."""
    problems: list[str] = []
    if settings.environment != "production":
        # Real money only moves in production: a live key on a laptop or a test server is
        # one mistake away from charging real customers.
        if _stripe_key(settings).startswith(LIVE_STRIPE_KEY_PREFIXES):
            problems.append(
                "STRIPE_SECRET_KEY is a live key; live keys are only allowed with "
                "ENVIRONMENT=production (use a test key, sk_test_...)"
            )
        return problems

    if not settings.rate_limit_enabled:
        problems.append("RATE_LIMIT_ENABLED must be true in production")
    if not settings.enforce_member_limits:
        problems.append("ENFORCE_MEMBER_LIMITS must be true in production")
    if any(origin == "*" or not origin.startswith("https://") for origin in settings.cors_origins):
        problems.append("CORS_ORIGINS may only list https:// origins in production (no *)")
    if settings.billing_enabled and not settings.app_base_url.startswith("https://"):
        problems.append(
            "APP_BASE_URL must be an https:// address in production when billing is enabled"
        )
    return problems


def configuration_warnings(settings: Settings) -> list[str]:
    """Allowed, but worth a line in the startup log."""
    if settings.environment != "production":
        return []
    warnings: list[str] = []
    if _stripe_key(settings).startswith(TEST_STRIPE_KEY_PREFIXES):
        warnings.append("Stripe is in test mode: no real payments are taken")
    if settings.billing_enabled and settings.stripe_webhook_secret is None:
        warnings.append("STRIPE_WEBHOOK_SECRET is not set: plans will not change after a payment")
    if not settings.ai_enabled:
        warnings.append("OPENAI_API_KEY is not set: AI insights are switched off")
    return warnings


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so the environment is read only once."""
    return Settings()
