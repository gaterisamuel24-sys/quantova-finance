"""Billing endpoints. Any member can see the plan and usage; changes come in step 6.2."""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.api.deps import OrgViewer, SessionDep, SettingsDep
from app.schemas.billing import BillingResponse, billing_response
from app.services.billing.entitlements import get_entitlements

router = APIRouter(prefix="/orgs/{org_id}/billing", tags=["billing"])


@router.get("", response_model=BillingResponse)
async def get_billing(
    ctx: OrgViewer, session: SessionDep, settings: SettingsDep
) -> BillingResponse:
    """The organization's plan, its limits, what has been used, and the available plans."""
    entitlements = await get_entitlements(
        session, ctx.organization.id, settings, now=datetime.now(UTC)
    )
    return billing_response(entitlements)
