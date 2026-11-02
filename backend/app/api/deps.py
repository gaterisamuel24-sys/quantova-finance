"""Shared FastAPI dependencies: settings, database session, client info, current user, RBAC."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import TokenValidationError, decode_access_token
from app.db.session import get_db_session
from app.models import OrgRole, User
from app.models.enums import org_role_at_least
from app.repositories import organizations as org_repo
from app.repositories import users as user_repo
from app.services.audit import ClientInfo
from app.services.organizations import OrgContext

MAX_USER_AGENT_LENGTH = 512

# auto_error=False: we raise our own 401 (with the correct WWW-Authenticate header).
bearer_scheme = HTTPBearer(auto_error=False)


def get_settings_dependency(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_client_info(request: Request) -> ClientInfo:
    user_agent = request.headers.get("user-agent")
    return ClientInfo(
        ip_address=request.client.host if request.client else None,
        user_agent=user_agent[:MAX_USER_AGENT_LENGTH] if user_agent else None,
    )


SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
ClientInfoDep = Annotated[ClientInfo, Depends(get_client_info)]


async def get_current_user(
    session: SessionDep,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Resolve the bearer access token to an active user, or reject with 401."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        claims = decode_access_token(credentials.credentials, settings)
    except TokenValidationError:
        raise unauthorized from None

    user = await user_repo.get_user_by_id(session, claims.user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_org_role(
    minimum: OrgRole,
) -> Callable[[uuid.UUID, AsyncSession, User], Awaitable[OrgContext]]:
    """Build a dependency that admits only members of {org_id} with at least `minimum` role.

    Non-members receive 404 (not 403), so the existence of other tenants'
    organizations is never revealed.
    """

    async def dependency(
        org_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
    ) -> OrgContext:
        found = await org_repo.get_organization_for_member(
            session, organization_id=org_id, user_id=current_user.id
        )
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found."
            )
        organization, membership = found
        if not org_role_at_least(membership.role, minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires the {minimum.value} role or higher.",
            )
        return OrgContext(organization=organization, membership=membership, user=current_user)

    return dependency


OrgViewer = Annotated[OrgContext, Depends(require_org_role(OrgRole.VIEWER))]
OrgAnalyst = Annotated[OrgContext, Depends(require_org_role(OrgRole.ANALYST))]
OrgAdmin = Annotated[OrgContext, Depends(require_org_role(OrgRole.ADMIN))]
OrgOwner = Annotated[OrgContext, Depends(require_org_role(OrgRole.OWNER))]
