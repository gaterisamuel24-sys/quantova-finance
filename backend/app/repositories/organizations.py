"""Organization and membership queries."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Membership, Organization, OrgRole, User


async def slug_exists(session: AsyncSession, slug: str) -> bool:
    found = await session.scalar(select(Organization.id).where(Organization.slug == slug))
    return found is not None


async def get_organization_for_member(
    session: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[Organization, Membership] | None:
    """Return the organization only if the user is a member of it. One query, one join."""
    statement = (
        select(Organization, Membership)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Organization.id == organization_id, Membership.user_id == user_id)
    )
    row = (await session.execute(statement)).first()
    return (row[0], row[1]) if row else None


async def list_organizations_for_user(
    session: AsyncSession, user_id: uuid.UUID
) -> list[tuple[Organization, OrgRole]]:
    statement = (
        select(Organization, Membership.role)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user_id)
        .order_by(Organization.name)
    )
    return [(organization, role) for organization, role in await session.execute(statement)]


async def list_members(
    session: AsyncSession, organization_id: uuid.UUID
) -> list[tuple[Membership, User]]:
    statement = (
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == organization_id)
        .order_by(Membership.created_at)
    )
    return [(membership, user) for membership, user in await session.execute(statement)]


async def get_membership(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    for_update: bool = False,
) -> Membership | None:
    statement = select(Membership).where(
        Membership.organization_id == organization_id, Membership.user_id == user_id
    )
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def count_owners_locked(session: AsyncSession, organization_id: uuid.UUID) -> int:
    """Count owners while locking their rows, so two concurrent demotions can't both succeed."""
    statement = (
        select(Membership.id)
        .where(Membership.organization_id == organization_id, Membership.role == OrgRole.OWNER)
        .with_for_update()
    )
    return len((await session.scalars(statement)).all())
