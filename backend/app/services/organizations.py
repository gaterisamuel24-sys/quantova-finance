"""Organization and membership use cases, including the role-management rules."""

import re
import secrets
import unicodedata
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Membership, Organization, OrgRole, User
from app.repositories import organizations as org_repo
from app.repositories import users as user_repo
from app.services.audit import ClientInfo, record_audit_event
from app.services.billing.entitlements import member_allowance
from app.services.defaults import add_default_ledger

MAX_SLUG_BASE_LENGTH = 80
ROLES_ADMINS_MAY_MANAGE = frozenset({OrgRole.ANALYST, OrgRole.VIEWER})


class OrganizationError(Exception):
    """Base class for organization rule violations."""


class UserNotFoundError(OrganizationError):
    pass


class MemberAlreadyExistsError(OrganizationError):
    pass


class MembershipNotFoundError(OrganizationError):
    pass


class RoleChangeForbiddenError(OrganizationError):
    pass


class LastOwnerError(OrganizationError):
    pass


class MemberLimitReachedError(OrganizationError):
    """The organization's plan allows no more members."""


@dataclass(frozen=True)
class OrgContext:
    """The organization being accessed, and the current user's membership in it."""

    organization: Organization
    membership: Membership
    user: User

    @property
    def role(self) -> OrgRole:
        return self.membership.role


def slugify(name: str) -> str:
    """'Café Ltd.' -> 'cafe-ltd'. Falls back to 'org' if nothing usable remains."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug[:MAX_SLUG_BASE_LENGTH].strip("-") or "org"


async def _unique_slug(session: AsyncSession, name: str) -> str:
    base = slugify(name)
    slug = base
    while await org_repo.slug_exists(session, slug):
        slug = f"{base}-{secrets.token_hex(3)}"
    return slug


def _ensure_can_manage(
    actor_role: OrgRole, target_role: OrgRole, new_role: OrgRole | None = None
) -> None:
    """Owners manage everyone; admins manage only analysts and viewers; nobody else manages."""
    if actor_role is OrgRole.OWNER:
        return
    if (
        actor_role is OrgRole.ADMIN
        and target_role in ROLES_ADMINS_MAY_MANAGE
        and (new_role is None or new_role in ROLES_ADMINS_MAY_MANAGE)
    ):
        return
    raise RoleChangeForbiddenError


async def _ensure_not_last_owner(session: AsyncSession, ctx: OrgContext) -> None:
    if await org_repo.count_owners_locked(session, ctx.organization.id) <= 1:
        raise LastOwnerError


async def create_organization(
    session: AsyncSession,
    *,
    user: User,
    name: str,
    base_currency: str,
    fiscal_year_start_month: int,
    client: ClientInfo,
) -> Organization:
    organization = Organization(
        name=name,
        slug=await _unique_slug(session, name),
        base_currency=base_currency,
        fiscal_year_start_month=fiscal_year_start_month,
    )
    session.add(organization)
    await session.flush()
    session.add(Membership(user_id=user.id, organization_id=organization.id, role=OrgRole.OWNER))
    add_default_ledger(session, organization)
    record_audit_event(
        session,
        action="organization.created",
        actor_user_id=user.id,
        organization_id=organization.id,
        entity_type="organization",
        entity_id=organization.id,
        details={"name": name, "slug": organization.slug},
        client=client,
    )
    await session.commit()
    await session.refresh(organization)
    return organization


async def update_organization(
    session: AsyncSession, ctx: OrgContext, *, changes: dict[str, Any], client: ClientInfo
) -> Organization:
    organization = ctx.organization
    diff: dict[str, dict[str, Any]] = {}
    for field, new_value in changes.items():
        old_value = getattr(organization, field)
        if old_value != new_value:
            setattr(organization, field, new_value)
            diff[field] = {"old": old_value, "new": new_value}

    if diff:
        record_audit_event(
            session,
            action="organization.updated",
            actor_user_id=ctx.user.id,
            organization_id=organization.id,
            entity_type="organization",
            entity_id=organization.id,
            details={"changes": diff},
            client=client,
        )
        await session.commit()
        await session.refresh(organization)
    return organization


async def add_member(
    session: AsyncSession,
    ctx: OrgContext,
    *,
    email: str,
    role: OrgRole,
    client: ClientInfo,
    enforce_limit: bool = True,
) -> tuple[Membership, User]:
    _ensure_can_manage(ctx.role, role)

    user = await user_repo.get_user_by_email(session, email)
    if user is None or not user.is_active:
        raise UserNotFoundError
    existing = await org_repo.get_membership(
        session, organization_id=ctx.organization.id, user_id=user.id
    )
    if existing is not None:
        raise MemberAlreadyExistsError

    if enforce_limit:
        # Lock the organization row so two simultaneous invitations cannot both slip in
        # under the limit; the lock is released when this transaction ends.
        await session.execute(
            select(Organization.id).where(Organization.id == ctx.organization.id).with_for_update()
        )
        plan, members = await member_allowance(session, ctx.organization.id)
        if members >= plan.max_members:
            raise MemberLimitReachedError

    membership = Membership(user_id=user.id, organization_id=ctx.organization.id, role=role)
    session.add(membership)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise MemberAlreadyExistsError from exc

    record_audit_event(
        session,
        action="membership.added",
        actor_user_id=ctx.user.id,
        organization_id=ctx.organization.id,
        entity_type="user",
        entity_id=user.id,
        details={"role": role.value},
        client=client,
    )
    await session.commit()
    await session.refresh(membership)
    return membership, user


async def change_member_role(
    session: AsyncSession,
    ctx: OrgContext,
    *,
    target_user_id: Any,
    new_role: OrgRole,
    client: ClientInfo,
) -> tuple[Membership, User]:
    target = await org_repo.get_membership(
        session, organization_id=ctx.organization.id, user_id=target_user_id, for_update=True
    )
    if target is None:
        raise MembershipNotFoundError
    _ensure_can_manage(ctx.role, target.role, new_role)
    if target.role is OrgRole.OWNER and new_role is not OrgRole.OWNER:
        await _ensure_not_last_owner(session, ctx)

    old_role = target.role
    if old_role is not new_role:
        target.role = new_role
        record_audit_event(
            session,
            action="membership.role_changed",
            actor_user_id=ctx.user.id,
            organization_id=ctx.organization.id,
            entity_type="user",
            entity_id=target.user_id,
            details={"old_role": old_role.value, "new_role": new_role.value},
            client=client,
        )
        await session.commit()
        await session.refresh(target)

    user = await user_repo.get_user_by_id(session, target.user_id)
    if user is None:
        raise MembershipNotFoundError
    return target, user


async def remove_member(
    session: AsyncSession, ctx: OrgContext, *, target_user_id: Any, client: ClientInfo
) -> None:
    target = await org_repo.get_membership(
        session, organization_id=ctx.organization.id, user_id=target_user_id, for_update=True
    )
    if target is None:
        raise MembershipNotFoundError

    is_self = target.user_id == ctx.user.id
    if not is_self:
        _ensure_can_manage(ctx.role, target.role)
    if target.role is OrgRole.OWNER:
        await _ensure_not_last_owner(session, ctx)

    removed_role = target.role
    await session.delete(target)
    record_audit_event(
        session,
        action="membership.removed",
        actor_user_id=ctx.user.id,
        organization_id=ctx.organization.id,
        entity_type="user",
        entity_id=target_user_id,
        details={"role": removed_role.value, "left_voluntarily": is_self},
        client=client,
    )
    await session.commit()
