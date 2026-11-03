"""Members per organization follow the plan: Free 1, Pro 5, Business 25."""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.helpers import create_user, run_query
from tests.test_analytics_api import execute_sql
from tests.test_transactions_api import Workspace, make_workspace

pytestmark = pytest.mark.integration


@pytest.fixture
def client(integration_settings: Settings, migrated_database: str) -> Iterator[TestClient]:
    # The rest of the suite switches member limits off; these tests switch them back on.
    settings = integration_settings.model_copy(update={"enforce_member_limits": True})
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def invite(client: TestClient, ws: Workspace, role: str = "analyst") -> int:
    user = create_user(client)
    response = client.post(
        f"{ws.url}/members", json={"email": user.email, "role": role}, headers=ws.owner.headers
    )
    return response.status_code


def set_plan(database_url: str, ws: Workspace, plan: str, status: str) -> None:
    """Stand-in for a verified webhook: insert or update the organization's subscription."""
    execute_sql(
        database_url,
        "INSERT INTO subscriptions (id, organization_id, plan, status, provider) "
        "VALUES (:id, :org_id, :plan, :status, 'stripe') "
        "ON CONFLICT (organization_id) DO UPDATE SET plan = :plan, status = :status",
        id=uuid.uuid4(),
        org_id=uuid.UUID(ws.org_id),
        plan=plan,
        status=status,
    )


def member_count(database_url: str, ws: Workspace) -> int:
    rows = run_query(
        database_url,
        "SELECT count(*) AS n FROM memberships WHERE organization_id = :org_id",
        org_id=uuid.UUID(ws.org_id),
    )
    return int(rows[0]["n"])


def test_the_free_plan_has_one_member(client: TestClient, migrated_database: str) -> None:
    ws = make_workspace(client)
    user = create_user(client)

    response = client.post(
        f"{ws.url}/members", json={"email": user.email, "role": "viewer"}, headers=ws.owner.headers
    )

    assert response.status_code == 402
    assert "member limit" in response.json()["detail"]
    assert member_count(migrated_database, ws) == 1  # nothing was added


def test_pro_allows_five_members(client: TestClient, migrated_database: str) -> None:
    ws = make_workspace(client)
    set_plan(migrated_database, ws, "pro", "active")

    statuses = [invite(client, ws) for _ in range(5)]

    assert statuses == [201, 201, 201, 201, 402]  # the owner plus four
    assert member_count(migrated_database, ws) == 5


def test_a_cancelled_plan_keeps_existing_members_but_adds_no_more(
    client: TestClient, migrated_database: str
) -> None:
    ws = make_workspace(client)
    set_plan(migrated_database, ws, "pro", "active")
    assert [invite(client, ws) for _ in range(2)] == [201, 201]

    set_plan(migrated_database, ws, "pro", "canceled")

    assert invite(client, ws) == 402
    assert member_count(migrated_database, ws) == 3  # nobody loses access on a downgrade
    usage = client.get(f"{ws.url}/billing", headers=ws.owner.headers).json()["usage"]
    assert (usage["members"], usage["max_members"]) == (3, 1)


def test_limit_applies_after_role_checks(client: TestClient) -> None:
    ws = make_workspace(client)
    # Owners may add owners; the plan limit (not a role rule) is what stops this one.
    assert invite(client, ws, role="owner") == 402
