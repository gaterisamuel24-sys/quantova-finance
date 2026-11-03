"""Turn verified Stripe webhook events into plain, typed changes. No database access.

Stripe's payloads are read defensively: only the fields we need, with their types
checked, so an unexpected shape is ignored rather than crashing the webhook. Field
locations that moved between Stripe API versions (current_period_end) are read
from both places.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.services.billing.plans import PlanId, SubscriptionStatus

SUBSCRIPTION_EVENTS = frozenset(
    {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.paused",
        "customer.subscription.resumed",
    }
)
CHECKOUT_COMPLETED = "checkout.session.completed"
PAYMENT_FAILED = "invoice.payment_failed"


@dataclass(frozen=True)
class SubscriptionChange:
    """The provider's current view of one subscription."""

    organization_id: uuid.UUID | None  # from our metadata; None if missing
    customer_id: str
    subscription_id: str
    plan: PlanId | None  # None if the price is not one of ours
    status: SubscriptionStatus
    current_period_end: datetime | None
    cancel_at_period_end: bool
    event_created: datetime


@dataclass(frozen=True)
class CheckoutCompleted:
    """A checkout finished: links the organization to its provider customer early."""

    organization_id: uuid.UUID
    customer_id: str
    subscription_id: str | None
    plan: PlanId | None
    event_created: datetime


@dataclass(frozen=True)
class PaymentFailed:
    customer_id: str
    subscription_id: str | None
    event_created: datetime


def _str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _id(value: object) -> str | None:
    """Stripe sends references either as an id string or as an expanded object with an id."""
    if isinstance(value, dict):
        return _str(value.get("id"))
    return _str(value)


def _uuid(value: object) -> uuid.UUID | None:
    text = _str(value)
    if text is None:
        return None
    try:
        return uuid.UUID(text)
    except ValueError:
        return None


def _timestamp(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return datetime.fromtimestamp(value, tz=UTC)


def _metadata(obj: dict[str, Any]) -> dict[str, Any]:
    metadata = obj.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _plan(value: object) -> PlanId | None:
    try:
        return PlanId(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _first_item(subscription: dict[str, Any]) -> dict[str, Any]:
    items = subscription.get("items")
    data = items.get("data") if isinstance(items, dict) else None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return {}


def plan_for_price(price_id: str | None, prices: dict[str, PlanId]) -> PlanId | None:
    return prices.get(price_id) if price_id else None


def parse_event(
    event: dict[str, Any], prices: dict[str, PlanId]
) -> SubscriptionChange | CheckoutCompleted | PaymentFailed | None:
    """The change an event describes, or None if we do not act on it."""
    event_type = event.get("type")
    created = _timestamp(event.get("created"))
    data = event.get("data")
    obj = data.get("object") if isinstance(data, dict) else None
    if created is None or not isinstance(obj, dict):
        return None

    if event_type in SUBSCRIPTION_EVENTS:
        subscription_id = _str(obj.get("id"))
        customer_id = _id(obj.get("customer"))
        raw_status = _str(obj.get("status"))
        try:
            status = SubscriptionStatus(raw_status or "")
        except ValueError:
            return None
        if subscription_id is None or customer_id is None:
            return None
        item = _first_item(obj)
        price = item.get("price")
        price_id = _id(price)
        period_end = _timestamp(item.get("current_period_end")) or _timestamp(
            obj.get("current_period_end")
        )
        return SubscriptionChange(
            organization_id=_uuid(_metadata(obj).get("organization_id")),
            customer_id=customer_id,
            subscription_id=subscription_id,
            # Our price ids decide the plan; metadata is only a fallback.
            plan=plan_for_price(price_id, prices) or _plan(_metadata(obj).get("plan")),
            status=(
                SubscriptionStatus.CANCELED
                if event_type == "customer.subscription.deleted"
                else status
            ),
            current_period_end=period_end,
            cancel_at_period_end=obj.get("cancel_at_period_end") is True,
            event_created=created,
        )

    if event_type == CHECKOUT_COMPLETED:
        if obj.get("mode") != "subscription":
            return None
        organization_id = _uuid(obj.get("client_reference_id")) or _uuid(
            _metadata(obj).get("organization_id")
        )
        customer_id = _id(obj.get("customer"))
        if organization_id is None or customer_id is None:
            return None
        return CheckoutCompleted(
            organization_id=organization_id,
            customer_id=customer_id,
            subscription_id=_id(obj.get("subscription")),
            plan=_plan(_metadata(obj).get("plan")),
            event_created=created,
        )

    if event_type == PAYMENT_FAILED:
        customer_id = _id(obj.get("customer"))
        if customer_id is None:
            return None
        return PaymentFailed(
            customer_id=customer_id,
            subscription_id=_id(obj.get("subscription")),
            event_created=created,
        )

    return None
