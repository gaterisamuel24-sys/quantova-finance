"""Organization and membership endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import ClientInfoDep, CurrentUser, OrgAdmin, OrgViewer, SessionDep, SettingsDep
from app.models import Membership, Organization, OrgRole, User
from app.repositories import organizations as org_repo
from app.schemas.organization import (
    MemberAdd,
    MemberResponse,
    MemberRoleUpdate,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services import organizations as org_service

router = APIRouter(prefix="/orgs", tags=["organizations"])

_ERROR_RESPONSES: dict[type[org_service.OrganizationError], tuple[int, str]] = {
    org_service.RoleChangeForbiddenError: (
        status.HTTP_403_FORBIDDEN,
        "Your role does not allow this change.",
    ),
    org_service.UserNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "No active user with that email address.",
    ),
    org_service.MembershipNotFoundError: (status.HTTP_404_NOT_FOUND, "Member not found."),
    org_service.MemberAlreadyExistsError: (
        status.HTTP_409_CONFLICT,
        "That user is already a member.",
    ),
    org_service.LastOwnerError: (
        status.HTTP_409_CONFLICT,
        "An organization must keep at least one owner.",
    ),
    org_service.MemberLimitReachedError: (
        status.HTTP_402_PAYMENT_REQUIRED,
        "This plan's member limit has been reached. Upgrade the plan to add more members.",
    ),
}


def _http_error(exc: org_service.OrganizationError) -> HTTPException:
    status_code, detail = _ERROR_RESPONSES[type(exc)]
    return HTTPException(status_code=status_code, detail=detail)


def _organization_response(organization: Organization, role: OrgRole) -> OrganizationResponse:
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        base_currency=organization.base_currency,
        fiscal_year_start_month=organization.fiscal_year_start_month,
        created_at=organization.created_at,
        my_role=role,
    )


def _member_response(membership: Membership, user: User) -> MemberResponse:
    return MemberResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        joined_at=membership.created_at,
    )


# ── Organizations ─────────────────────────────────────


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    session: SessionDep,
    current_user: CurrentUser,
    client: ClientInfoDep,
) -> OrganizationResponse:
    organization = await org_service.create_organization(
        session,
        user=current_user,
        name=payload.name,
        base_currency=payload.base_currency,
        fiscal_year_start_month=payload.fiscal_year_start_month,
        client=client,
    )
    return _organization_response(organization, OrgRole.OWNER)


@router.get("", response_model=list[OrganizationResponse])
async def list_my_organizations(
    session: SessionDep, current_user: CurrentUser
) -> list[OrganizationResponse]:
    rows = await org_repo.list_organizations_for_user(session, current_user.id)
    return [_organization_response(organization, role) for organization, role in rows]


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(ctx: OrgViewer) -> OrganizationResponse:
    return _organization_response(ctx.organization, ctx.role)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    payload: OrganizationUpdate, ctx: OrgAdmin, session: SessionDep, client: ClientInfoDep
) -> OrganizationResponse:
    organization = await org_service.update_organization(
        session, ctx, changes=payload.model_dump(exclude_unset=True), client=client
    )
    return _organization_response(organization, ctx.role)


# ── Members ───────────────────────────────────────────


@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members(ctx: OrgViewer, session: SessionDep) -> list[MemberResponse]:
    rows = await org_repo.list_members(session, ctx.organization.id)
    return [_member_response(membership, user) for membership, user in rows]


@router.post(
    "/{org_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED
)
async def add_member(
    payload: MemberAdd,
    ctx: OrgAdmin,
    session: SessionDep,
    settings: SettingsDep,
    client: ClientInfoDep,
) -> MemberResponse:
    try:
        membership, user = await org_service.add_member(
            session,
            ctx,
            email=payload.email,
            role=payload.role,
            client=client,
            enforce_limit=settings.enforce_member_limits,
        )
    except org_service.OrganizationError as exc:
        raise _http_error(exc) from exc
    return _member_response(membership, user)


@router.patch("/{org_id}/members/{user_id}", response_model=MemberResponse)
async def change_member_role(
    user_id: uuid.UUID,
    payload: MemberRoleUpdate,
    ctx: OrgAdmin,
    session: SessionDep,
    client: ClientInfoDep,
) -> MemberResponse:
    try:
        membership, user = await org_service.change_member_role(
            session, ctx, target_user_id=user_id, new_role=payload.role, client=client
        )
    except org_service.OrganizationError as exc:
        raise _http_error(exc) from exc
    return _member_response(membership, user)


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: uuid.UUID, ctx: OrgViewer, session: SessionDep, client: ClientInfoDep
) -> Response:
    # Viewer is the minimum so any member can leave; removing others is checked in the service.
    try:
        await org_service.remove_member(session, ctx, target_user_id=user_id, client=client)
    except org_service.OrganizationError as exc:
        raise _http_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
