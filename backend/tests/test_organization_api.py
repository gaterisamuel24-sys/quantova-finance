"""End-to-end tests for organizations, memberships and role-based access control."""

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.helpers import ORGS, TestUser, create_user, run_query

pytestmark = pytest.mark.integration


@pytest.fixture
def client(integration_settings: Settings, migrated_database: str) -> Iterator[TestClient]:
    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


def unique_name(prefix: str = "Acme Ltd") -> str:
    return f"{prefix} {uuid.uuid4().hex[:6]}"


def create_org(client: TestClient, owner: TestUser, **fields: Any) -> dict[str, Any]:
    payload = {"name": unique_name(), **fields}
    response = client.post(ORGS, json=payload, headers=owner.headers)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def add_member(client: TestClient, actor: TestUser, org_id: str, email: str, role: str) -> int:
    """Try to add a member; return the HTTP status code."""
    response = client.post(
        f"{ORGS}/{org_id}/members", json={"email": email, "role": role}, headers=actor.headers
    )
    return response.status_code


# ── Organizations ─────────────────────────────────────


def test_create_organization_makes_creator_owner(client: TestClient) -> None:
    owner = create_user(client)
    name = unique_name()

    org = create_org(client, owner, name=name)

    assert org["my_role"] == "owner"
    assert org["slug"] == name.lower().replace(" ", "-")
    assert org["base_currency"] == "USD"
    listed = client.get(ORGS, headers=owner.headers).json()
    assert [item["id"] for item in listed] == [org["id"]]


def test_same_name_gets_unique_slugs(client: TestClient) -> None:
    owner = create_user(client)
    name = unique_name()

    first = create_org(client, owner, name=name)
    second = create_org(client, owner, name=name)

    assert second["slug"] != first["slug"]
    assert second["slug"].startswith(f"{first['slug']}-")


def test_organization_input_is_validated(client: TestClient) -> None:
    owner = create_user(client)

    assert create_org(client, owner, base_currency="kes")["base_currency"] == "KES"
    for invalid in ({"base_currency": "KESH"}, {"fiscal_year_start_month": 13}):
        response = client.post(ORGS, json={"name": "X", **invalid}, headers=owner.headers)
        assert response.status_code == 422


def test_requires_authentication(client: TestClient) -> None:
    assert client.post(ORGS, json={"name": "Nope"}).status_code == 401


# ── Tenant isolation ──────────────────────────────────


def test_outsiders_cannot_see_an_organization(client: TestClient) -> None:
    owner, outsider = create_user(client), create_user(client)
    org = create_org(client, owner)

    # 404, not 403: outsiders must not learn that the organization exists.
    assert client.get(f"{ORGS}/{org['id']}", headers=outsider.headers).status_code == 404
    members = client.get(f"{ORGS}/{org['id']}/members", headers=outsider.headers)
    assert members.status_code == 404
    assert client.get(ORGS, headers=outsider.headers).json() == []


# ── Roles ─────────────────────────────────────────────


def test_only_admins_and_owners_can_edit_settings(client: TestClient) -> None:
    owner, viewer = create_user(client), create_user(client)
    org = create_org(client, owner)
    assert add_member(client, owner, org["id"], viewer.email, "viewer") == 201
    url = f"{ORGS}/{org['id']}"

    assert client.patch(url, json={"name": "Hijacked"}, headers=viewer.headers).status_code == 403
    assert client.patch(url, json={"name": None}, headers=owner.headers).status_code == 422
    updated = client.patch(url, json={"name": "Renamed Ltd"}, headers=owner.headers)
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed Ltd"


def test_adding_members(client: TestClient) -> None:
    owner, member = create_user(client), create_user(client)
    org = create_org(client, owner)

    assert add_member(client, owner, org["id"], member.email, "analyst") == 201
    assert add_member(client, owner, org["id"], member.email, "viewer") == 409
    assert add_member(client, owner, org["id"], "nobody@example.com", "viewer") == 404

    members = client.get(f"{ORGS}/{org['id']}/members", headers=member.headers).json()
    assert {(m["email"], m["role"]) for m in members} == {
        (owner.email, "owner"),
        (member.email, "analyst"),
    }


def test_admins_cannot_escalate_privileges(client: TestClient) -> None:
    owner, admin, other = create_user(client), create_user(client), create_user(client)
    org = create_org(client, owner)
    assert add_member(client, owner, org["id"], admin.email, "admin") == 201
    members_url = f"{ORGS}/{org['id']}/members"

    assert add_member(client, admin, org["id"], other.email, "admin") == 403
    assert add_member(client, admin, org["id"], other.email, "analyst") == 201
    promote = client.patch(
        f"{members_url}/{other.user_id}", json={"role": "owner"}, headers=admin.headers
    )
    assert promote.status_code == 403
    remove_owner = client.delete(f"{members_url}/{owner.user_id}", headers=admin.headers)
    assert remove_owner.status_code == 403


def test_last_owner_cannot_be_demoted_or_removed(client: TestClient) -> None:
    owner, co_owner = create_user(client), create_user(client)
    org = create_org(client, owner)
    owner_url = f"{ORGS}/{org['id']}/members/{owner.user_id}"

    demote = client.patch(owner_url, json={"role": "admin"}, headers=owner.headers)
    assert demote.status_code == 409
    assert client.delete(owner_url, headers=owner.headers).status_code == 409

    assert add_member(client, owner, org["id"], co_owner.email, "owner") == 201
    demote = client.patch(owner_url, json={"role": "admin"}, headers=owner.headers)
    assert demote.status_code == 200
    assert demote.json()["role"] == "admin"


def test_members_can_leave(client: TestClient) -> None:
    owner, member = create_user(client), create_user(client)
    org = create_org(client, owner)
    assert add_member(client, owner, org["id"], member.email, "viewer") == 201

    leave = client.delete(f"{ORGS}/{org['id']}/members/{member.user_id}", headers=member.headers)

    assert leave.status_code == 204
    assert client.get(f"{ORGS}/{org['id']}", headers=member.headers).status_code == 404


# ── Audit trail ───────────────────────────────────────


def test_organization_changes_are_audited(client: TestClient, migrated_database: str) -> None:
    owner, member = create_user(client), create_user(client)
    org = create_org(client, owner)
    assert add_member(client, owner, org["id"], member.email, "viewer") == 201
    client.patch(f"{ORGS}/{org['id']}", json={"fiscal_year_start_month": 7}, headers=owner.headers)

    events = run_query(
        migrated_database,
        "SELECT action, details FROM audit_logs WHERE organization_id = :org_id",
        org_id=uuid.UUID(org["id"]),
    )

    actions = {event["action"] for event in events}
    assert {"organization.created", "membership.added", "organization.updated"} <= actions
    update = next(e for e in events if e["action"] == "organization.updated")
    assert update["details"]["changes"]["fiscal_year_start_month"] == {"old": 1, "new": 7}
