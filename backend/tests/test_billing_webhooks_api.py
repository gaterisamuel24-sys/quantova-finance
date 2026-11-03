"""The Stripe webhook endpoint: signatures, idempotency, ordering and plan changes."""

import hashlib
import hmac
import json
import time
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app
from tests.helpers import run_query
from tests.test_transactions_api import Workspace, make_workspace

pytestmark = pytest.mark.integration

WEBHOOK = "/api/v1/billing/webhooks/stripe"
SECRET = "whsec_test_not_a_real_secret"


@pytest.fixture
def client(integration_settings: Settings, migrated_database: str) -> Iterator[TestClient]:
    settings = integration_settings.model_copy(
        update={
            "stripe_webhook_secret": SecretStr(SECRET),
            "stripe_price_pro": "price_pro_test",
            "stripe_price_business": "price_business_test",
        }
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def sign(payload: str, *, secret: str = SECRET, timestamp: int | None = None) -> str:
    """A Stripe-Signature header: HMAC-SHA256 of "<timestamp>.<payload>" with the secret."""
    ts = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(secret.encode(), f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def deliver(client: TestClient, event: dict[str, Any], **sign_options: Any) -> tuple[int, str]:
    payload = json.dumps(event)
    response = client.post(
        WEBHOOK,
        content=payload,
        headers={
            "Stripe-Signature": sign(payload, **sign_options),
            "Content-Type": "application/json",
        },
    )
    return response.status_code, response.json().get("status", response.json().get("detail"))


def subscription_event(
    ws: Workspace,
    *,
    status: str = "active",
    price: str = "price_pro_test",
    created: int = 1_793_000_000,
    event_type: str = "customer.subscription.updated",
    subscription_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": event_type,
        "created": created,
        "data": {
            "object": {
                "id": subscription_id or f"sub_{ws.org_id.replace('-', '')}",
                "customer": customer_id or f"cus_{ws.org_id.replace('-', '')}",
                "status": status,
                "cancel_at_period_end": False,
                "metadata": {"organization_id": ws.org_id, "plan": "pro"},
                "items": {
                    "data": [{"price": {"id": price}, "current_period_end": created + 2_592_000}]
                },
            }
        },
    }


def plan_of(client: TestClient, ws: Workspace) -> tuple[str, str | None]:
    body = client.get(f"{ws.url}/billing", headers=ws.owner.headers).json()
    return body["plan"]["id"], body["status"]


# ── Signatures ────────────────────────────────────────


def test_rejects_missing_wrong_and_replayed_signatures(client: TestClient) -> None:
    ws = make_workspace(client)
    event = subscription_event(ws)

    missing = client.post(WEBHOOK, content=json.dumps(event))
    wrong_secret = deliver(client, event, secret="whsec_attacker")
    replayed = deliver(client, event, timestamp=int(time.time()) - 3600)  # an hour old

    assert missing.status_code == 400
    assert wrong_secret[0] == 400
    assert replayed[0] == 400
    assert plan_of(client, ws) == ("free", None)  # nothing was applied


def test_without_a_webhook_secret_the_endpoint_is_off(
    integration_settings: Settings, migrated_database: str
) -> None:
    with TestClient(create_app(integration_settings)) as client:
        response = client.post(WEBHOOK, content="{}", headers={"Stripe-Signature": "t=1,v1=x"})

    assert response.status_code == 503


# ── Applying events ───────────────────────────────────


def test_checkout_then_subscription_upgrades_the_organization(
    client: TestClient, migrated_database: str
) -> None:
    ws = make_workspace(client)
    checkout = {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": "checkout.session.completed",
        "created": 1_793_000_000,
        "data": {
            "object": {
                "mode": "subscription",
                "client_reference_id": ws.org_id,
                "customer": f"cus_{ws.org_id.replace('-', '')}",
                "subscription": f"sub_{ws.org_id.replace('-', '')}",
                "metadata": {"plan": "business"},
            }
        },
    }

    assert deliver(client, checkout) == (200, "applied")
    assert plan_of(client, ws) == ("free", "incomplete")  # no paid access until it is paid

    created = subscription_event(
        ws,
        price="price_business_test",
        event_type="customer.subscription.created",
        created=1_793_000_010,
    )
    assert deliver(client, created) == (200, "applied")
    assert plan_of(client, ws) == ("business", "active")

    audit = run_query(
        migrated_database,
        "SELECT details->>'new_plan' AS plan, details->>'new_status' AS status FROM audit_logs "
        "WHERE organization_id = :org_id AND action = 'billing.subscription_updated'",
        org_id=uuid.UUID(ws.org_id),
    )
    assert audit == [{"plan": "business", "status": "active"}]


def test_a_repeated_delivery_is_applied_once(client: TestClient) -> None:
    ws = make_workspace(client)
    event = subscription_event(ws)

    assert deliver(client, event) == (200, "applied")
    assert deliver(client, event) == (200, "duplicate")


def test_events_arriving_out_of_order(client: TestClient) -> None:
    ws = make_workspace(client)
    cancelled = subscription_event(
        ws, event_type="customer.subscription.deleted", status="canceled", created=1_793_000_100
    )
    older_active = subscription_event(ws, status="active", created=1_793_000_050)

    assert deliver(client, cancelled) == (200, "applied")
    assert deliver(client, older_active) == (200, "stale")
    assert plan_of(client, ws) == ("free", "canceled")


def test_failed_payment_keeps_access_while_retried(client: TestClient) -> None:
    ws = make_workspace(client)
    deliver(client, subscription_event(ws, created=1_793_000_000))

    deliver(client, subscription_event(ws, status="past_due", created=1_793_000_500))

    assert plan_of(client, ws) == ("pro", "past_due")


def test_an_old_subscription_ending_does_not_cancel_the_new_one(client: TestClient) -> None:
    ws = make_workspace(client)
    deliver(client, subscription_event(ws, subscription_id="sub_new", created=1_793_000_100))

    old_ends = subscription_event(
        ws,
        subscription_id="sub_old",
        event_type="customer.subscription.deleted",
        status="canceled",
        created=1_793_000_200,
    )

    assert deliver(client, old_ends) == (200, "ignored")
    assert plan_of(client, ws) == ("pro", "active")


def test_events_for_unknown_organizations_are_ignored(client: TestClient) -> None:
    ws = make_workspace(client)
    event = subscription_event(ws)
    event["data"]["object"]["metadata"]["organization_id"] = str(uuid.uuid4())
    event["data"]["object"]["id"] = "sub_nobody"
    event["data"]["object"]["customer"] = "cus_nobody"

    assert deliver(client, event) == (200, "ignored")
    assert plan_of(client, ws) == ("free", None)


def test_unrelated_events_are_accepted_and_ignored(client: TestClient) -> None:
    event = {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": "charge.refunded",
        "created": 1,
        "data": {"object": {}},
    }

    assert deliver(client, event) == (200, "ignored")
