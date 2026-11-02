"""Authentication use cases: registration, login, refresh-token rotation and logout.

Each public function is one unit of work and commits its own transaction.
Failures are raised as domain exceptions; the API layer turns them into HTTP responses.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models import RefreshToken, User
from app.repositories import refresh_tokens as refresh_token_repo
from app.repositories import users as user_repo
from app.services.audit import ClientInfo, record_audit_event


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str


async def register_user(
    session: AsyncSession, *, email: str, password: str, full_name: str, client: ClientInfo
) -> User:
    if await user_repo.get_user_by_email(session, email) is not None:
        raise EmailAlreadyRegisteredError

    password_hash = await run_in_threadpool(hash_password, password)
    user = User(email=email, password_hash=password_hash, full_name=full_name)
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        # Another request registered the same email between our check and our insert.
        await session.rollback()
        raise EmailAlreadyRegisteredError from exc

    record_audit_event(
        session,
        action="user.registered",
        actor_user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        client=client,
    )
    await session.commit()
    await session.refresh(user)
    return user


async def login(
    session: AsyncSession, settings: Settings, *, email: str, password: str, client: ClientInfo
) -> IssuedTokens:
    user = await user_repo.get_user_by_email(session, email)
    is_valid, updated_hash = await run_in_threadpool(
        verify_password, password, user.password_hash if user else None
    )

    if user is None or not is_valid or not user.is_active:
        reason = "unknown_email" if user is None else ("inactive" if is_valid else "wrong_password")
        record_audit_event(
            session,
            action="auth.login_failed",
            actor_user_id=user.id if user else None,
            details={"reason": reason},
            client=client,
        )
        await session.commit()
        raise InvalidCredentialsError

    now = datetime.now(UTC)
    if updated_hash is not None:
        user.password_hash = updated_hash
    user.last_login_at = now

    refresh_token = _add_refresh_token(
        session, settings, user_id=user.id, family_id=uuid.uuid7(), client=client, now=now
    )
    record_audit_event(session, action="auth.login_succeeded", actor_user_id=user.id, client=client)
    await session.commit()
    return IssuedTokens(create_access_token(user.id, settings, now=now), refresh_token)


async def rotate_refresh_token(
    session: AsyncSession, settings: Settings, *, refresh_token: str, client: ClientInfo
) -> IssuedTokens:
    now = datetime.now(UTC)
    stored = await refresh_token_repo.get_by_hash_for_update(
        session, hash_refresh_token(refresh_token)
    )
    if stored is None:
        raise InvalidRefreshTokenError

    if stored.revoked_at is not None:
        # A token that was already used has been presented again: someone holds a copy.
        # Revoke the whole family so neither the thief nor the victim's copy works.
        await refresh_token_repo.revoke_family(session, stored.family_id, now)
        record_audit_event(
            session,
            action="auth.refresh_token_reuse_detected",
            actor_user_id=stored.user_id,
            details={"family_id": str(stored.family_id)},
            client=client,
        )
        await session.commit()
        raise InvalidRefreshTokenError

    if stored.expires_at <= now:
        raise InvalidRefreshTokenError

    user = await user_repo.get_user_by_id(session, stored.user_id)
    if user is None or not user.is_active:
        await refresh_token_repo.revoke_family(session, stored.family_id, now)
        await session.commit()
        raise InvalidRefreshTokenError

    stored.revoked_at = now
    new_refresh_token = _add_refresh_token(
        session, settings, user_id=user.id, family_id=stored.family_id, client=client, now=now
    )
    await session.commit()
    return IssuedTokens(create_access_token(user.id, settings, now=now), new_refresh_token)


async def logout(session: AsyncSession, *, refresh_token: str, client: ClientInfo) -> None:
    now = datetime.now(UTC)
    stored = await refresh_token_repo.get_by_hash_for_update(
        session, hash_refresh_token(refresh_token)
    )
    if stored is None:
        return
    await refresh_token_repo.revoke_family(session, stored.family_id, now)
    record_audit_event(session, action="auth.logout", actor_user_id=stored.user_id, client=client)
    await session.commit()


def _add_refresh_token(
    session: AsyncSession,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    family_id: uuid.UUID,
    client: ClientInfo,
    now: datetime,
) -> str:
    """Create a refresh token, store its hash, and return the plain token (shown once)."""
    token = generate_refresh_token()
    session.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(token),
            family_id=family_id,
            expires_at=now + timedelta(days=settings.refresh_token_ttl_days),
            user_agent=client.user_agent,
            ip_address=client.ip_address,
        )
    )
    return token
