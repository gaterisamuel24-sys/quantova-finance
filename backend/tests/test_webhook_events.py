"""Reading Stripe webhook payloads into typed changes (no database, no network)."""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.services.billing.plans import PlanId, SubscriptionStatus
from app.services.billing.webhook_events import (
    CheckoutCompleted,
    PaymentFailed,
    SubscriptionChange,
    parse_event,
)

PRICES = {"price_pro": PlanId.PRO, "price_business": PlanId.BUSINESS}
ORG_ID = uuid.uuid4()
CREATED = 1_793_000_000  # a Unix timestamp in 2026


def subscription_event(
    event_type: str = "customer.subscription.updated", **fields: Any
) -> dict[str, Any]:
    obj: dict[str, Any] = {
        "id": "sub_123",
        "object": "subscription",
        "customer": "cus_123",
        "status": "active",
        "cancel_at_period_end": False,
        "metadata": {"organization_id": str(ORG_ID), "plan": "pro"},
        "items": {
            "data": [{"price": {"id": "price_business"}, "current_period_end": CREATED + 86_400}]
        },
    }
    obj.update(fields)
    return {"id": "evt_1", "type": event_type, "created": CREATED, "data": {"object": obj}}


def test_reads_a_subscription_update() -> None:
    change = parse_event(subscription_event(), PRICES)

    assert change == SubscriptionChange(
        organization_id=ORG_ID,
        customer_id="cus_123",
        subscription_id="sub_123",
        plan=PlanId.BUSINESS,  # the price decides, not the (older) metadata
        status=SubscriptionStatus.ACTIVE,
        current_period_end=datetime.fromtimestamp(CREATED + 86_400, tz=UTC),
        cancel_at_period_end=False,
        event_created=datetime.fromtimestamp(CREATED, tz=UTC),
    )


def test_deleted_means_canceled() -> None:
    change = parse_event(subscription_event("customer.subscription.deleted"), PRICES)

    assert isinstance(change, SubscriptionChange)
    assert change.status is SubscriptionStatus.CANCELED


def test_unknown_price_falls_back_to_metadata() -> None:
    event = subscription_event(items={"data": [{"price": {"id": "price_someone_else"}}]})

    change = parse_event(event, PRICES)

    assert isinstance(change, SubscriptionChange)
    assert change.plan is PlanId.PRO
    assert change.current_period_end is None


def test_older_payloads_with_period_end_on_the_subscription() -> None:
    event = subscription_event(
        items={"data": [{"price": "price_pro"}]}, current_period_end=CREATED + 60
    )

    change = parse_event(event, PRICES)

    assert isinstance(change, SubscriptionChange)
    assert change.plan is PlanId.PRO  # a price given as a plain id string
    assert change.current_period_end == datetime.fromtimestamp(CREATED + 60, tz=UTC)


@pytest.mark.parametrize(
    "broken",
    [
        {"status": "on_fire"},
        {"customer": None},
        {"id": 42},
        {"metadata": "not-a-dict", "items": "nope", "status": "bogus"},
    ],
)
def test_malformed_subscription_payloads_are_ignored(broken: dict[str, Any]) -> None:
    assert parse_event(subscription_event(**broken), PRICES) is None


def test_bad_organization_id_in_metadata_is_dropped() -> None:
    event = subscription_event(metadata={"organization_id": "'; DROP TABLE x;--"})

    change = parse_event(event, PRICES)

    assert isinstance(change, SubscriptionChange)
    assert change.organization_id is None


def test_reads_a_completed_checkout() -> None:
    event = {
        "id": "evt_2",
        "type": "checkout.session.completed",
        "created": CREATED,
        "data": {
            "object": {
                "mode": "subscription",
                "client_reference_id": str(ORG_ID),
                "customer": "cus_9",
                "subscription": "sub_9",
                "metadata": {"plan": "business"},
            }
        },
    }

    assert parse_event(event, PRICES) == CheckoutCompleted(
        organization_id=ORG_ID,
        customer_id="cus_9",
        subscription_id="sub_9",
        plan=PlanId.BUSINESS,
        event_created=datetime.fromtimestamp(CREATED, tz=UTC),
    )


def test_reads_a_failed_payment() -> None:
    event = {
        "id": "evt_3",
        "type": "invoice.payment_failed",
        "created": CREATED,
        "data": {"object": {"customer": "cus_9", "subscription": {"id": "sub_9"}}},
    }

    assert parse_event(event, PRICES) == PaymentFailed(
        customer_id="cus_9",
        subscription_id="sub_9",
        event_created=datetime.fromtimestamp(CREATED, tz=UTC),
    )


@pytest.mark.parametrize(
    "event",
    [
        {"type": "charge.refunded", "created": CREATED, "data": {"object": {}}},
        {"type": "customer.subscription.updated", "created": "yesterday", "data": {"object": {}}},
        {"type": "customer.subscription.updated", "created": CREATED, "data": None},
        {
            "type": "checkout.session.completed",
            "created": CREATED,
            "data": {"object": {"mode": "payment", "customer": "cus_1"}},
        },
    ],
)
def test_events_we_do_not_act_on(event: dict[str, Any]) -> None:
    assert parse_event(event, PRICES) is None
