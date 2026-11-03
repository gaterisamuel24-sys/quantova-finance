"""Starting a subscription checkout and opening the billing portal, for one organization.

These only create hosted pages at the provider. Nothing about the subscription changes
here: the provider reports the outcome through verified webhooks (step 6.3).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.services.audit import ClientInfo, record_audit_event
from app.services.billing.entitlements import get_subscription
from app.services.billing.plans import PAID_ACCESS, PlanId
from app.services.billing.provider import BillingProvider, CheckoutRequest
from app.services.organizations import OrgContext


class BillingStateError(Exception):
    """The request does not fit the organization's current subscription."""


def billing_page_url(settings: Settings, ctx: OrgContext, result: str | None = None) -> str:
    url = f"{settings.app_base_url}/app/{ctx.organization.id}/billing"
    return f"{url}?checkout={result}" if result else url


async def start_checkout(
    session: AsyncSession,
    ctx: OrgContext,
    provider: BillingProvider,
    settings: Settings,
    *,
    plan: PlanId,
    client: ClientInfo,
) -> str:
    if plan is PlanId.FREE:
        raise BillingStateError("The Free plan needs no checkout.")
    subscription = await get_subscription(session, ctx.organization.id)
    if subscription is not None and subscription.status in PAID_ACCESS:
        # Changing between paid plans, or cancelling, happens in the provider's portal,
        # which handles proration and avoids creating a second subscription.
        raise BillingStateError(
            "This organization already has a paid plan. Use Manage billing to change it."
        )

    url = await provider.create_checkout(
        CheckoutRequest(
            organization_id=ctx.organization.id,
            plan=plan,
            customer_id=subscription.provider_customer_id if subscription else None,
            customer_email=ctx.user.email,
            success_url=billing_page_url(settings, ctx, "success"),
            cancel_url=billing_page_url(settings, ctx, "cancelled"),
        )
    )
    record_audit_event(
        session,
        action="billing.checkout_started",
        actor_user_id=ctx.user.id,
        organization_id=ctx.organization.id,
        entity_type="subscription",
        details={"plan": plan.value, "provider": provider.name},
        client=client,
    )
    await session.commit()
    return url


async def open_portal(
    session: AsyncSession,
    ctx: OrgContext,
    provider: BillingProvider,
    settings: Settings,
    *,
    client: ClientInfo,
) -> str:
    subscription = await get_subscription(session, ctx.organization.id)
    if subscription is None or subscription.provider_customer_id is None:
        raise BillingStateError("There is no billing account yet. Choose a plan first.")

    url = await provider.create_portal(
        customer_id=subscription.provider_customer_id,
        return_url=billing_page_url(settings, ctx),
    )
    record_audit_event(
        session,
        action="billing.portal_opened",
        actor_user_id=ctx.user.id,
        organization_id=ctx.organization.id,
        entity_type="subscription",
        entity_id=subscription.id,
        details={"provider": provider.name},
        client=client,
    )
    await session.commit()
    return url
