"""Billing endpoints.

Any member can see the plan and usage. Only owners can start a checkout or open the
billing portal, because those commit the organization to payments.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.api.deps import ClientInfoDep, OrgOwner, OrgViewer, SessionDep, SettingsDep
from app.schemas.billing import BillingResponse, billing_response
from app.services.billing import service as billing_service
from app.services.billing.entitlements import get_entitlements
from app.services.billing.plans import PlanId
from app.services.billing.provider import (
    BillingProvider,
    BillingProviderError,
    BillingUnavailableError,
)
from app.services.billing.stripe_provider import build_billing_provider

router = APIRouter(prefix="/orgs/{org_id}/billing", tags=["billing"])


class CheckoutStart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan: PlanId


class RedirectResponse(BaseModel):
    """A provider-hosted page to send the browser to."""

    url: str


def get_billing_provider(settings: SettingsDep) -> BillingProvider:
    """The configured payment provider. Tests replace this dependency with a fake."""
    try:
        return build_billing_provider(settings)
    except BillingUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured on this server.",
        ) from None


BillingProviderDep = Annotated[BillingProvider, Depends(get_billing_provider)]


@router.get("", response_model=BillingResponse)
async def get_billing(
    ctx: OrgViewer, session: SessionDep, settings: SettingsDep
) -> BillingResponse:
    """The organization's plan, its limits, what has been used, and the available plans."""
    entitlements = await get_entitlements(
        session, ctx.organization.id, settings, now=datetime.now(UTC)
    )
    return billing_response(entitlements, billing_enabled=settings.billing_enabled)


@router.post("/checkout", response_model=RedirectResponse)
async def start_checkout(
    payload: CheckoutStart,
    ctx: OrgOwner,
    session: SessionDep,
    settings: SettingsDep,
    client: ClientInfoDep,
    provider: BillingProviderDep,
) -> RedirectResponse:
    """Start paying for a plan on the provider's hosted checkout page."""
    try:
        url = await billing_service.start_checkout(
            session, ctx, provider, settings, plan=payload.plan, client=client
        )
    except billing_service.BillingStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except BillingProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return RedirectResponse(url=url)


@router.post("/portal", response_model=RedirectResponse)
async def open_portal(
    ctx: OrgOwner,
    session: SessionDep,
    settings: SettingsDep,
    client: ClientInfoDep,
    provider: BillingProviderDep,
) -> RedirectResponse:
    """Open the provider's portal to change plan, cancel, update the card or see invoices."""
    try:
        url = await billing_service.open_portal(session, ctx, provider, settings, client=client)
    except billing_service.BillingStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except BillingProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return RedirectResponse(url=url)
