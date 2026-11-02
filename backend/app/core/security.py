"""Password hashing, access-token signing and refresh-token generation.

Pure functions with no database access, so every rule here is unit-testable.
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import Settings

ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - a JWT "type" claim value, not a credential

_password_hasher = PasswordHash((Argon2Hasher(),))

# Hash of a random value nobody knows. Verifying against it when a user does not
# exist makes "unknown email" take as long as "wrong password", so response
# timing cannot reveal which email addresses have accounts.
_DUMMY_PASSWORD_HASH = _password_hasher.hash(secrets.token_urlsafe(32))


class TokenValidationError(Exception):
    """Raised for any invalid, expired, tampered or wrong-type access token."""


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    token_id: str
    issued_at: datetime
    expires_at: datetime


# ── Passwords ─────────────────────────────────────────


def hash_password(password: str) -> str:
    """Return an Argon2id hash (algorithm, parameters and random salt are embedded in it)."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> tuple[bool, str | None]:
    """Check a password against a stored hash.

    Returns (is_valid, updated_hash). updated_hash is set when the stored hash uses
    outdated parameters; save it after a successful login so hashes stay current.
    Pass password_hash=None for an unknown user: a dummy hash is still verified,
    so the call takes the same time either way.
    """
    if password_hash is None:
        _password_hasher.verify(password, _DUMMY_PASSWORD_HASH)
        return False, None
    return _password_hasher.verify_and_update(password, password_hash)


# ── Access tokens (JWT) ───────────────────────────────


def create_access_token(
    user_id: uuid.UUID, settings: Settings, *, now: datetime | None = None
) -> str:
    """Issue a short-lived signed access token for a user."""
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "jti": uuid.uuid4().hex,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": issued_at,
        "nbf": issued_at,
        "exp": issued_at + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(
        payload, settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str, settings: Settings) -> AccessTokenClaims:
    """Verify signature, expiry, issuer, audience and type; return the claims.

    Raises TokenValidationError for any problem, with a deliberately generic message.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "type", "jti", "iss", "aud", "iat", "exp"]},
        )
        if payload["type"] != ACCESS_TOKEN_TYPE:
            raise TokenValidationError("Invalid or expired access token")
        return AccessTokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            token_id=payload["jti"],
            issued_at=datetime.fromtimestamp(payload["iat"], UTC),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise TokenValidationError("Invalid or expired access token") from exc


# ── Refresh tokens (opaque) ───────────────────────────


def generate_refresh_token() -> str:
    """256 bits of randomness, URL-safe. Sent to the client once; never stored in plain form."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex digest used to store and look up refresh tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
