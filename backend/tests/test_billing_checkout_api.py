"""Upgrading and managing billing through the API, with a fake payment provider."""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.v1.billing import get_billing_provider
from app.core.config import Settings
from app.main import create_app
from tests.fake_billing import FakeBillingProvider
from tests.helpers import create_user, run_query
from tests.test_analytics_api import execute_sql
from tests.test_transactions_api import Workspace, make_workspace

pytestmark = pytest.mark.integration


@pytest.fixture
def provider() -> FakeBillingProvider:
    return FakeBillingProvider()


@pytest.fixture
def client(
    integration_settings: Settings, migrated_database: str, provider: FakeBillingProvider
) -> Iterator[TestClient]:
    settings = integration_settings.model_copy(update={"app_base_url": "https://app.example"})
    app = create_app(settings)
    app.dependency_overrides[get_billing_provider] = lambda: provider
    with TestClient(app) as test_client:
        yield test_client


def subscribe(database_url: str, ws: Workspace, status: str, customer: str | None) -> None:
    execute_sql(
        database_url,
        "INSERT INTO subscriptions (id, organization_id, plan, status, provider, "
        "provider_customer_id) VALUES (:id, :org_id, 'pro', :status, 'stripe', :customer)",
        id=uuid.uuid4(),
        org_id=uuid.UUID(ws.org_id),
        status=status,
        customer=customer,
    )


def test_owner_starts_a_checkout(
    client: TestClient, provider: FakeBillingProvider, migrated_database: str
) -> None:
    ws = make_workspace(client)

    response = client.post(
        f"{ws.url}/billing/checkout", json={"plan": "pro"}, headers=ws.owner.headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["url"].startswith("https://checkout.stripe.com/")
    sent = provider.checkouts[0]
    assert str(sent.organization_id) == ws.org_id
    assert sent.customer_email == ws.owner.email
    assert sent.success_url == f"https://app.example/app/{ws.org_id}/billing?checkout=success"
    audit = run_query(
        migrated_database,
        "SELECT details->>'plan' AS plan FROM audit_logs "
        "WHERE organization_id = :org_id AND action = 'billing.checkout_started'",
        org_id=uuid.UUID(ws.org_id),
    )
    assert audit == [{"plan": "pro"}]


def test_only_owners_can_change_billing(client: TestClient, provider: FakeBillingProvider) -> None:
    ws = make_workspace(client)
    admin = create_user(client)
    added = client.post(
        f"{ws.url}/members", json={"email": admin.email, "role": "admin"}, headers=ws.owner.headers
    )
    assert added.status_code == 201

    checkout = client.post(
        f"{ws.url}/billing/checkout", json={"plan": "pro"}, headers=admin.headers
    )
    portal = client.post(f"{ws.url}/billing/portal", headers=admin.headers)

    assert (checkout.status_code, portal.status_code) == (403, 403)
    assert provider.checkouts == []


@pytest.mark.parametrize("body", [{"plan": "free"}, {"plan": "gold"}, {"plan": "pro", "price": 1}])
def test_rejects_invalid_checkout_requests(client: TestClient, body: dict[str, object]) -> None:
    ws = make_workspace(client)

    response = client.post(f"{ws.url}/billing/checkout", json=body, headers=ws.owner.headers)

    # "free" is a valid plan name but needs no checkout (409); the others are malformed (422).
    assert response.status_code == (409 if body == {"plan": "free"} else 422)


def test_no_second_subscription_while_one_is_active(
    client: TestClient, migrated_database: str
) -> None:
    ws = make_workspace(client)
    subscribe(migrated_database, ws, "active", "cus_live_1")

    response = client.post(
        f"{ws.url}/billing/checkout", json={"plan": "business"}, headers=ws.owner.headers
    )

    assert response.status_code == 409
    assert "Manage billing" in response.json()["detail"]


def test_a_cancelled_subscription_can_check_out_again_as_the_same_customer(
    client: TestClient, provider: FakeBillingProvider, migrated_database: str
) -> None:
    ws = make_workspace(client)
    subscribe(migrated_database, ws, "canceled", "cus_returning")

    response = client.post(
        f"{ws.url}/billing/checkout", json={"plan": "pro"}, headers=ws.owner.headers
    )

    assert response.status_code == 200
    assert provider.checkouts[0].customer_id == "cus_returning"


def test_portal_needs_a_billing_account(
    client: TestClient, provider: FakeBillingProvider, migrated_database: str
) -> None:
    ws = make_workspace(client)

    before = client.post(f"{ws.url}/billing/portal", headers=ws.owner.headers)
    subscribe(migrated_database, ws, "active", "cus_portal")
    after = client.post(f"{ws.url}/billing/portal", headers=ws.owner.headers)

    assert before.status_code == 409
    assert after.status_code == 200
    assert after.json()["url"].startswith("https://billing.stripe.com/")
    assert provider.portals == [("cus_portal", f"https://app.example/app/{ws.org_id}/billing")]


def test_provider_failure_is_reported(client: TestClient, provider: FakeBillingProvider) -> None:
    ws = make_workspace(client)
    provider.fail = True

    response = client.post(
        f"{ws.url}/billing/checkout", json={"plan": "pro"}, headers=ws.owner.headers
    )

    assert response.status_code == 502


def test_without_keys_billing_is_unavailable(
    integration_settings: Settings, migrated_database: str
) -> None:
    settings = integration_settings.model_copy(update={"stripe_secret_key": None})
    with TestClient(create_app(settings)) as client:
        ws = make_workspace(client)

        response = client.post(
            f"{ws.url}/billing/checkout", json={"plan": "pro"}, headers=ws.owner.headers
        )
        status = client.get(f"{ws.url}/billing", headers=ws.owner.headers).json()

    assert response.status_code == 503
    assert status["billing_enabled"] is False
