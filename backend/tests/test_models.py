"""Database-level guarantees: constraints, defaults and the append-only audit log."""

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Membership, Organization, OrgRole, PlatformRole, User

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

DUMMY_HASH = "not-a-real-argon2-hash"


def make_user(email: str = "alice@example.com") -> User:
    return User(email=email, password_hash=DUMMY_HASH, full_name="Alice Example")


async def test_user_defaults_are_applied(db_session: AsyncSession) -> None:
    user = make_user()
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    assert user.id.version == 7
    assert user.is_active is True
    assert user.is_email_verified is False
    assert user.platform_role is PlatformRole.USER
    assert user.created_at.tzinfo is not None


async def test_user_email_must_be_lowercase(db_session: AsyncSession) -> None:
    db_session.add(make_user(email="Alice@Example.com"))

    with pytest.raises(IntegrityError, match="ck_users_email_lowercase"):
        await db_session.flush()


async def test_user_email_is_unique(db_session: AsyncSession) -> None:
    db_session.add(make_user())
    await db_session.flush()
    db_session.add(make_user())

    with pytest.raises(IntegrityError, match="uq_users_email"):
        await db_session.flush()


async def test_organization_rejects_invalid_currency(db_session: AsyncSession) -> None:
    db_session.add(Organization(name="Acme", slug="acme", base_currency="usd"))

    with pytest.raises(IntegrityError, match="ck_organizations_base_currency_iso4217"):
        await db_session.flush()


async def test_membership_is_unique_per_user_and_organization(db_session: AsyncSession) -> None:
    user = make_user()
    organization = Organization(name="Acme", slug="acme")
    db_session.add_all([user, organization])
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=organization.id, role=OrgRole.OWNER))
    await db_session.flush()
    db_session.add(
        Membership(user_id=user.id, organization_id=organization.id, role=OrgRole.VIEWER)
    )

    with pytest.raises(IntegrityError, match="uq_memberships_user_id_organization_id"):
        await db_session.flush()


async def test_audit_log_rows_cannot_be_updated(db_session: AsyncSession) -> None:
    entry = AuditLog(action="test.created")
    db_session.add(entry)
    await db_session.flush()

    with pytest.raises(DBAPIError, match="append-only"):
        await db_session.execute(
            update(AuditLog).where(AuditLog.id == entry.id).values(action="tampered")
        )


async def test_audit_log_rows_cannot_be_deleted(db_session: AsyncSession) -> None:
    entry = AuditLog(action="test.created")
    db_session.add(entry)
    await db_session.flush()

    with pytest.raises(DBAPIError, match="append-only"):
        await db_session.execute(delete(AuditLog).where(AuditLog.id == entry.id))
