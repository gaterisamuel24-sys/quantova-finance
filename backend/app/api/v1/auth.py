"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from fastapi.responses import JSONResponse

from app.api.deps import ClientInfoDep, CurrentUser, SessionDep, SettingsDep
from app.core.config import Settings
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "quantova_refresh"
SECONDS_PER_DAY = 86_400

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)]


# ── Cookie helpers ────────────────────────────────────


def _cookie_path(settings: Settings) -> str:
    # The browser sends the refresh cookie only to the auth endpoints, never elsewhere.
    return f"{settings.api_v1_prefix}/auth"


def _cookie_secure(settings: Settings) -> bool:
    # HTTPS-only outside local development and tests (which run over plain http).
    return settings.environment in ("staging", "production")


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.refresh_token_ttl_days * SECONDS_PER_DAY,
        path=_cookie_path(settings),
        secure=_cookie_secure(settings),
        httponly=True,
        samesite="strict",
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=_cookie_path(settings),
        secure=_cookie_secure(settings),
        httponly=True,
        samesite="strict",
    )


def _token_response(access_token: str, settings: Settings) -> TokenResponse:
    return TokenResponse(
        access_token=access_token, expires_in=settings.access_token_ttl_minutes * 60
    )


def _session_rejected(settings: Settings) -> JSONResponse:
    response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Session expired. Please log in again."},
        headers={"WWW-Authenticate": "Bearer"},
    )
    _clear_refresh_cookie(response, settings)
    return response


# ── Endpoints ─────────────────────────────────────────


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: SessionDep, client: ClientInfoDep) -> User:
    try:
        return await auth_service.register_user(
            session,
            email=payload.email,
            password=payload.password.get_secret_value(),
            full_name=payload.full_name,
            client=client,
        )
    except auth_service.EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    client: ClientInfoDep,
) -> TokenResponse:
    try:
        tokens = await auth_service.login(
            session,
            settings,
            email=payload.email,
            password=payload.password.get_secret_value(),
            client=client,
        )
    except auth_service.InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    _set_refresh_cookie(response, tokens.refresh_token, settings)
    return _token_response(tokens.access_token, settings)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    client: ClientInfoDep,
    refresh_token: RefreshCookie = None,
) -> TokenResponse | JSONResponse:
    if refresh_token is None:
        return _session_rejected(settings)
    try:
        tokens = await auth_service.rotate_refresh_token(
            session, settings, refresh_token=refresh_token, client=client
        )
    except auth_service.InvalidRefreshTokenError:
        return _session_rejected(settings)

    _set_refresh_cookie(response, tokens.refresh_token, settings)
    return _token_response(tokens.access_token, settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    session: SessionDep,
    settings: SettingsDep,
    client: ClientInfoDep,
    refresh_token: RefreshCookie = None,
) -> Response:
    if refresh_token is not None:
        await auth_service.logout(session, refresh_token=refresh_token, client=client)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(response, settings)
    return response


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> User:
    return current_user
