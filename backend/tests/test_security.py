"""Unit tests for password hashing and token handling. No database required."""

import base64
import json
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.security import (
    TokenValidationError,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from tests.conftest import SettingsFactory

PASSWORD = "correct horse battery staple"


# ── Passwords ─────────────────────────────────────────


def test_password_hash_is_argon2id_and_never_contains_the_password() -> None:
    hashed = hash_password(PASSWORD)

    assert hashed.startswith("$argon2id$")
    assert PASSWORD not in hashed


def test_same_password_hashes_differently_each_time() -> None:
    # A random salt per hash means identical passwords are not identifiable in the database.
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_verify_password_accepts_correct_and_rejects_wrong() -> None:
    hashed = hash_password(PASSWORD)

    assert verify_password(PASSWORD, hashed) == (True, None)
    assert verify_password("wrong password", hashed)[0] is False


def test_verify_password_for_unknown_user_returns_false() -> None:
    assert verify_password(PASSWORD, None) == (False, None)


# ── Access tokens ─────────────────────────────────────


def test_access_token_round_trip(settings_factory: SettingsFactory) -> None:
    settings = settings_factory()
    user_id = uuid.uuid7()

    claims = decode_access_token(create_access_token(user_id, settings), settings)

    assert claims.user_id == user_id
    lifetime = claims.expires_at - claims.issued_at
    assert lifetime == timedelta(minutes=settings.access_token_ttl_minutes)


def test_expired_access_token_is_rejected(settings_factory: SettingsFactory) -> None:
    settings = settings_factory()
    long_ago = datetime.now(UTC) - timedelta(hours=1)
    token = create_access_token(uuid.uuid7(), settings, now=long_ago)

    with pytest.raises(TokenValidationError):
        decode_access_token(token, settings)


def test_tampered_access_token_is_rejected(settings_factory: SettingsFactory) -> None:
    settings = settings_factory()
    token = create_access_token(uuid.uuid7(), settings)
    header, _payload, signature = token.split(".")

    # Swap in a different user ID but keep the original signature.
    claims = jwt.decode(token, options={"verify_signature": False})
    claims["sub"] = str(uuid.uuid7())
    forged_payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()

    with pytest.raises(TokenValidationError):
        decode_access_token(f"{header}.{forged_payload}.{signature}", settings)


def test_token_signed_with_another_secret_is_rejected(settings_factory: SettingsFactory) -> None:
    attacker_settings = settings_factory(jwt_secret_key="attacker-" + "f" * 56)
    token = create_access_token(uuid.uuid7(), attacker_settings)

    with pytest.raises(TokenValidationError):
        decode_access_token(token, settings_factory())


def test_unsigned_alg_none_token_is_rejected(settings_factory: SettingsFactory) -> None:
    settings = settings_factory()
    claims = jwt.decode(
        create_access_token(uuid.uuid7(), settings), options={"verify_signature": False}
    )
    unsigned_token = jwt.encode(claims, "", algorithm="none")

    with pytest.raises(TokenValidationError):
        decode_access_token(unsigned_token, settings)


def test_token_for_another_audience_is_rejected(settings_factory: SettingsFactory) -> None:
    token = create_access_token(uuid.uuid7(), settings_factory(jwt_audience="another-app"))

    with pytest.raises(TokenValidationError):
        decode_access_token(token, settings_factory())


def test_token_of_wrong_type_is_rejected(settings_factory: SettingsFactory) -> None:
    settings = settings_factory()
    claims = jwt.decode(
        create_access_token(uuid.uuid7(), settings), options={"verify_signature": False}
    )
    claims["type"] = "password-reset"
    wrong_type_token = jwt.encode(
        claims, settings.jwt_secret_key.get_secret_value(), algorithm="HS256"
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(wrong_type_token, settings)


# ── Refresh tokens ────────────────────────────────────


def test_refresh_tokens_are_unique_and_high_entropy() -> None:
    tokens = {generate_refresh_token() for _ in range(100)}

    assert len(tokens) == 100
    assert all(len(token) >= 43 for token in tokens)  # 32 bytes, base64url-encoded


def test_refresh_token_hash_is_deterministic_sha256() -> None:
    token = generate_refresh_token()

    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert len(hash_refresh_token(token)) == 64
    assert hash_refresh_token(token) != hash_refresh_token(generate_refresh_token())
