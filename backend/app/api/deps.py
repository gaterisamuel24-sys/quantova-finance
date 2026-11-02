"""Shared FastAPI dependencies: settings, database session, client info and current user."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import TokenValidationError, decode_access_token
from app.db.session import get_db_session
from app.models import User
from app.repositories import users as user_repo
from app.services.audit import ClientInfo

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
