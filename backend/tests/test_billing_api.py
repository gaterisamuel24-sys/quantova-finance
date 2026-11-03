"""Billing status per organization, and plan limits applied to AI insights."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1.insights import get_insight_model
from app.core.config import Settings
from app.main import create_app
from tests.fake_ai import FakeInsightModel
from tests.helpers import create_user
from tests.test_analytics_api import execute_sql
from tests.test_insights_api import grounded_answer
from tests.test_transactions_api import Workspace, create_transaction, make_workspace

pytestmark = pytest.mark.integration

TODAY = datetime.now(UTC).date().isoformat()


@pytest.fixture
def client(integration_settings: Settings, migrated_database: str) -> Iterator[TestClient]:
    app = create_app(integration_settings)
    app.dependency_overrides[get_insight_model] = lambda: FakeInsightModel(respond=grounded_answer)
    with TestClient(app) as test_client:
        yield test_client


def billing(client: TestClient, ws: Workspace) -> dict[str, Any]:
    response = client.get(f"{ws.url}/billing", headers=ws.owner.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def subscribe(database_url: str, ws: Workspace, plan: str, status: str) -> None:
    """Stand-in for a verified provider webhook (step 6.3)."""
    execute_sql(
        database_url,
        "INSERT INTO subscriptions (id, organization_id, plan, status, provider) "
        "VALUES (:id, :org_id, :plan, :status, 'stripe')",
        id=uuid.uuid4(),
        org_id=uuid.UUID(ws.org_id),
        plan=plan,
        status=status,
    )


def test_new_organizations_are_on_the_free_plan(client: TestClient) -> None:
    ws = make_workspace(client)

    body = billing(client, ws)

    assert body["plan"] == {
        "id": "free",
        "name": "Free",
        "description": "For trying Quantova on your own.",
        "monthly_price_usd": "0",
        "max_members": 1,
        "ai_insights_per_day": 3,
    }
    assert body["status"] is None
    assert body["usage"] == {
        "members": 1,
        "max_members": 1,
        "ai_insights_today": 0,
        "ai_insights_per_day": 3,
    }
    assert [plan["id"] for plan in body["plans"]] == ["free", "pro", "business"]


def test_the_free_plan_allows_three_insights_a_day(client: TestClient) -> None:
    ws = make_workspace(client)
    create_transaction(client, ws, occurred_on=TODAY)

    statuses = [
        client.post(f"{ws.url}/insights", json={}, headers=ws.owner.headers).status_code
        for _ in range(4)
    ]

    assert statuses == [201, 201, 201, 429]
    last = client.post(f"{ws.url}/insights", json={}, headers=ws.owner.headers)
    assert "Free plan includes 3 insights a day" in last.json()["detail"]


@pytest.mark.parametrize(
    ("status", "plan", "insights_per_day"),
    [
        ("active", "pro", 20),
        ("past_due", "pro", 20),  # access continues while the payment is retried
        ("canceled", "free", 3),
        ("incomplete", "free", 3),
    ],
)
def test_limits_follow_the_subscription(
    client: TestClient, migrated_database: str, status: str, plan: str, insights_per_day: int
) -> None:
    ws = make_workspace(client)
    subscribe(migrated_database, ws, "pro", status)

    body = billing(client, ws)
    insights = client.get(f"{ws.url}/insights", headers=ws.owner.headers).json()

    assert body["plan"]["id"] == plan
    assert body["status"] == status
    assert insights["daily_limit"] == insights_per_day


def test_members_can_see_billing_but_outsiders_cannot(client: TestClient) -> None:
    ws = make_workspace(client)
    outsider = create_user(client)

    response = client.get(f"{ws.url}/billing", headers=outsider.headers)

    assert response.status_code == 404
