"""Apply verified payment-provider events to organizations' subscriptions.

Only this module changes the `subscriptions` table. Each event is recorded once in
`billing_events` in the same database transaction as the change it causes, so a
retried delivery is detected and skipped, and a crash never leaves half an update.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BillingEvent, Organization, Subscription
from app.services.audit import record_audit_event
from app.services.billing.plans import PAID_ACCESS, PlanId, SubscriptionStatus
from app.services.billing.webhook_events import (
    CheckoutCompleted,
    PaymentFailed,
    SubscriptionChange,
    parse_event,
)

logger = logging.getLogger(__name__)


async def _organization_exists(session: AsyncSession, organization_id: uuid.UUID) -> bool:
    found = await session.scalar(select(Organization.id).where(Organization.id == organization_id))
    return found is not None


async def _find_subscription(
    session: AsyncSession,
    *,
    subscription_id: str | None,
    customer_id: str | None,
    organization_id: uuid.UUID | None,
) -> Subscription | None:
    """The row this event belongs to: by provider subscription, then customer, then org."""
    conditions = []
    if subscription_id:
        conditions.append(Subscription.provider_subscription_id == subscription_id)
    if customer_id:
        conditions.append(Subscription.provider_customer_id == customer_id)
    if organization_id:
        conditions.append(Subscription.organization_id == organization_id)
    if not conditions:
        return None
    rows = (await session.scalars(select(Subscription).where(or_(*conditions)))).all()
    for key in ("provider_subscription_id", "provider_customer_id", "organization_id"):
        wanted = {
            "provider_subscription_id": subscription_id,
            "provider_customer_id": customer_id,
            "organization_id": organization_id,
        }[key]
        for row in rows:
            if wanted is not None and getattr(row, key) == wanted:
                return row
    return None


async def _apply_subscription_change(
    session: AsyncSession, provider: str, change: SubscriptionChange
) -> tuple[str, uuid.UUID | None]:
    row = await _find_subscription(
        session,
        subscription_id=change.subscription_id,
        customer_id=change.customer_id,
        organization_id=change.organization_id,
    )
    if row is None:
        if (
            change.organization_id is None
            or change.plan is None
            or not await _organization_exists(session, change.organization_id)
        ):
            logger.warning("Subscription event for an unknown organization was ignored")
            return "ignored", None
        row = Subscription(
            organization_id=change.organization_id,
            plan=change.plan,
            status=change.status,
            provider=provider,
        )
        session.add(row)
        old_plan, old_status = None, None
    else:
        if row.provider_updated_at and change.event_created < row.provider_updated_at:
            return "stale", row.organization_id
        old_plan, old_status = row.plan, row.status
        # An older subscription ending must not cancel the organization's current one.
        replaced = (
            row.provider_subscription_id is not None
            and row.provider_subscription_id != change.subscription_id
        )
        if replaced and row.status in PAID_ACCESS and change.status not in PAID_ACCESS:
            return "ignored", row.organization_id

    row.plan = change.plan or row.plan
    row.status = change.status
    row.provider_customer_id = change.customer_id
    row.provider_subscription_id = change.subscription_id
    row.current_period_end = change.current_period_end
    row.cancel_at_period_end = change.cancel_at_period_end
    row.provider_updated_at = change.event_created
    await session.flush()

    record_audit_event(
        session,
        action="billing.subscription_updated",
        organization_id=row.organization_id,
        entity_type="subscription",
        entity_id=row.id,
        details={
            "provider": provider,
            "old_plan": old_plan.value if old_plan else None,
            "new_plan": row.plan.value,
            "old_status": old_status.value if old_status else None,
            "new_status": row.status.value,
            "cancel_at_period_end": row.cancel_at_period_end,
        },
    )
    return "applied", row.organization_id


async def _apply_checkout(
    session: AsyncSession, provider: str, change: CheckoutCompleted
) -> tuple[str, uuid.UUID | None]:
    if not await _organization_exists(session, change.organization_id):
        return "ignored", None
    row = await session.scalar(
        select(Subscription).where(Subscription.organization_id == change.organization_id)
    )
    if row is None:
        # Payment status arrives with the subscription events; until then, no paid access.
        row = Subscription(
            organization_id=change.organization_id,
            plan=change.plan or PlanId.PRO,
            status=SubscriptionStatus.INCOMPLETE,
            provider=provider,
        )
        session.add(row)
    row.provider_customer_id = row.provider_customer_id or change.customer_id
    if change.subscription_id and row.status not in PAID_ACCESS:
        row.provider_subscription_id = change.subscription_id
    await session.flush()
    record_audit_event(
        session,
        action="billing.checkout_completed",
        organization_id=change.organization_id,
        entity_type="subscription",
        entity_id=row.id,
        details={"provider": provider, "plan": change.plan.value if change.plan else None},
    )
    return "applied", change.organization_id


async def _record_payment_failure(
    session: AsyncSession, provider: str, change: PaymentFailed
) -> tuple[str, uuid.UUID | None]:
    row = await _find_subscription(
        session,
        subscription_id=change.subscription_id,
        customer_id=change.customer_id,
        organization_id=None,
    )
    if row is None:
        return "ignored", None
    # The status change (past_due) arrives as a subscription event; this is for the record.
    record_audit_event(
        session,
        action="billing.payment_failed",
        organization_id=row.organization_id,
        entity_type="subscription",
        entity_id=row.id,
        details={"provider": provider},
    )
    return "applied", row.organization_id


async def handle_event(
    session: AsyncSession, event: dict[str, Any], *, provider: str, prices: dict[str, PlanId]
) -> str:
    """Process one verified event exactly once. Returns its outcome, or "duplicate"."""
    event_id = event.get("id")
    event_type = event.get("type")
    if not isinstance(event_id, str) or not isinstance(event_type, str):
        return "ignored"

    record = BillingEvent(
        provider=provider, event_id=event_id[:255], event_type=event_type[:100], outcome="ignored"
    )
    session.add(record)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return "duplicate"

    change = parse_event(event, prices)
    outcome, organization_id = "ignored", None
    if isinstance(change, SubscriptionChange):
        outcome, organization_id = await _apply_subscription_change(session, provider, change)
    elif isinstance(change, CheckoutCompleted):
        outcome, organization_id = await _apply_checkout(session, provider, change)
    elif isinstance(change, PaymentFailed):
        outcome, organization_id = await _record_payment_failure(session, provider, change)

    record.outcome = outcome
    record.organization_id = organization_id
    await session.commit()
    return outcome
