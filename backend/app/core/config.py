"""Application settings, loaded from environment variables (and .env in development)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
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

    # ── AI insights (optional) ─────────────────────────
    # Without OPENAI_API_KEY the AI features are switched off; everything else works.
    openai_api_key: SecretStr | None = None
    openai_model: str = Field(default="gpt-5.4-mini", min_length=1, max_length=100)
    ai_request_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    ai_max_output_tokens: int = Field(default=1500, ge=200, le=8000)
    # Server-wide safety cap on AI insights per organization per day. The plan's own
    # allowance applies below it (Free 3, Pro 20, Business 100).
    ai_daily_insights_per_org: int = Field(default=100, ge=1, le=1000)

    @property
    def ai_enabled(self) -> bool:
        return self.openai_api_key is not None

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def blank_key_means_no_key(cls, value: object) -> object:
        # "OPENAI_API_KEY=" in .env (an empty value) must switch AI off, not send "" to OpenAI.
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def jwt_secret_must_be_strong(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET_KEY must be at least {MIN_JWT_SECRET_LENGTH} characters; "
                "generate 64 random hex characters (see backend/.env.example)"
            )
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so the environment is read only once."""
    return Settings()
