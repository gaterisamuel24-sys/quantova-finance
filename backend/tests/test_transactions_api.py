"""End-to-end tests for accounts, categories and transactions."""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
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


@dataclass(frozen=True)
class Workspace:
    """A fresh organization with its owner and starter ledger."""

    owner: TestUser
    org_id: str
    account_id: str
    income_category_id: str
    expense_category_id: str

    @property
    def url(self) -> str:
        return f"{ORGS}/{self.org_id}"


def make_workspace(client: TestClient) -> Workspace:
    owner = create_user(client)
    created = client.post(
        ORGS,
        json={"name": f"Ledger {uuid.uuid4().hex[:6]}", "base_currency": "KES"},
        headers=owner.headers,
    )
    assert created.status_code == 201, created.text
    org_id = created.json()["id"]
    accounts = client.get(f"{ORGS}/{org_id}/accounts", headers=owner.headers).json()
    categories = client.get(f"{ORGS}/{org_id}/categories", headers=owner.headers).json()
    by_name = {category["name"]: category["id"] for category in categories}
    return Workspace(
        owner=owner,
        org_id=org_id,
        account_id=accounts[0]["id"],
        income_category_id=by_name["Sales"],
        expense_category_id=by_name["Rent & utilities"],
    )


def payload(ws: Workspace, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "kind": "income",
        "amount": "1250.50",
        "occurred_on": "2026-10-15",
        "account_id": ws.account_id,
        "category_id": ws.income_category_id,
        "description": "Consulting invoice #1042",
    }
    body.update(overrides)
    return body


def create_transaction(client: TestClient, ws: Workspace, **overrides: Any) -> dict[str, Any]:
    response = client.post(
        f"{ws.url}/transactions", json=payload(ws, **overrides), headers=ws.owner.headers
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def error_field(body: dict[str, Any]) -> str:
    """The field named by the first entry of a 422 error body."""
    return str(body["detail"][0]["loc"][-1])


# ── Accounts and categories ───────────────────────────


def test_lists_the_starter_ledger(client: TestClient) -> None:
    ws = make_workspace(client)

    accounts = client.get(f"{ws.url}/accounts", headers=ws.owner.headers).json()
    categories = client.get(f"{ws.url}/categories", headers=ws.owner.headers).json()

    assert [(a["name"], a["currency"]) for a in accounts] == [("Main account", "KES")]
    assert Decimal(accounts[0]["opening_balance"]) == 0
    assert len(categories) == 14
    assert {c["kind"] for c in categories} == {"income", "expense"}


# ── Exact money ───────────────────────────────────────


def test_amounts_are_stored_and_returned_exactly(client: TestClient) -> None:
    ws = make_workspace(client)

    created = create_transaction(client, ws, amount="1250.5")
    fetched = client.get(f"{ws.url}/transactions/{created['id']}", headers=ws.owner.headers)

    assert isinstance(created["amount"], str)  # money travels as a string, never a float
    assert Decimal(created["amount"]) == Decimal("1250.5")
    assert created["currency"] == "KES"  # taken from the account, not the client
    assert fetched.json()["amount"] == created["amount"]


@pytest.mark.parametrize("bad_amount", [1250.5, "1.23456", "-5", "0", "1e3"])
def test_rejects_inexact_or_non_positive_amounts(client: TestClient, bad_amount: object) -> None:
    ws = make_workspace(client)

    response = client.post(
        f"{ws.url}/transactions", json=payload(ws, amount=bad_amount), headers=ws.owner.headers
    )

    assert response.status_code == 422
    assert error_field(response.json()) == "amount"


def test_rejects_dates_far_in_the_future(client: TestClient) -> None:
    ws = make_workspace(client)

    response = client.post(
        f"{ws.url}/transactions",
        json=payload(ws, occurred_on="2099-01-01"),
        headers=ws.owner.headers,
    )

    assert response.status_code == 422
    assert error_field(response.json()) == "occurred_on"


# ── Validation against the organization's ledger ──────


def test_category_must_match_the_transaction_kind(client: TestClient) -> None:
    ws = make_workspace(client)

    response = client.post(
        f"{ws.url}/transactions",
        json=payload(ws, kind="income", category_id=ws.expense_category_id),
        headers=ws.owner.headers,
    )

    assert response.status_code == 422
    assert error_field(response.json()) == "category_id"


def test_tenants_cannot_use_or_see_each_others_ledgers(client: TestClient) -> None:
    alpha, beta = make_workspace(client), make_workspace(client)
    alpha_transaction = create_transaction(client, alpha)

    # Beta tries to book a transaction against Alpha's account.
    response = client.post(
        f"{beta.url}/transactions",
        json=payload(beta, account_id=alpha.account_id),
        headers=beta.owner.headers,
    )
    assert response.status_code == 422
    assert error_field(response.json()) == "account_id"

    # Beta cannot read Alpha's transaction, through either organization's URL.
    via_alpha = f"{alpha.url}/transactions/{alpha_transaction['id']}"
    via_beta = f"{beta.url}/transactions/{alpha_transaction['id']}"
    assert client.get(via_alpha, headers=beta.owner.headers).status_code == 404
    assert client.get(via_beta, headers=beta.owner.headers).status_code == 404


def test_viewers_can_read_but_not_write(client: TestClient) -> None:
    ws = make_workspace(client)
    viewer = create_user(client)
    added = client.post(
        f"{ws.url}/members",
        json={"email": viewer.email, "role": "viewer"},
        headers=ws.owner.headers,
    )
    assert added.status_code == 201

    assert client.get(f"{ws.url}/transactions", headers=viewer.headers).status_code == 200
    write = client.post(f"{ws.url}/transactions", json=payload(ws), headers=viewer.headers)
    assert write.status_code == 403


# ── Listing ───────────────────────────────────────────


def test_lists_newest_first_with_filters_and_pages(client: TestClient) -> None:
    ws = make_workspace(client)
    create_transaction(client, ws, occurred_on="2026-09-01", amount="100")
    create_transaction(
        client,
        ws,
        kind="expense",
        category_id=ws.expense_category_id,
        occurred_on="2026-09-15",
        amount="40",
    )
    create_transaction(client, ws, occurred_on="2026-10-01", amount="250")
    url, headers = f"{ws.url}/transactions", ws.owner.headers

    first = client.get(url, params={"page_size": 2}, headers=headers).json()
    second = client.get(url, params={"page_size": 2, "page": 2}, headers=headers).json()
    expenses = client.get(url, params={"kind": "expense"}, headers=headers).json()
    september = client.get(
        url, params={"date_from": "2026-09-10", "date_to": "2026-09-30"}, headers=headers
    ).json()

    assert first["total"] == 3
    assert [t["occurred_on"] for t in first["items"]] == ["2026-10-01", "2026-09-15"]
    assert [t["occurred_on"] for t in second["items"]] == ["2026-09-01"]
    assert expenses["total"] == 1
    assert september["total"] == 1


def test_search_treats_wildcards_literally(client: TestClient) -> None:
    ws = make_workspace(client)
    create_transaction(client, ws, description="Promo: 100% off setup fee")
    create_transaction(client, ws, description="Monthly retainer")
    url = f"{ws.url}/transactions"

    percent = client.get(url, params={"q": "%"}, headers=ws.owner.headers).json()
    retainer = client.get(url, params={"q": "RETAINER"}, headers=ws.owner.headers).json()

    assert percent["total"] == 1  # "%" matches only the text containing a real percent sign
    assert retainer["total"] == 1  # search is case-insensitive


def test_rejects_an_inverted_date_range(client: TestClient) -> None:
    ws = make_workspace(client)

    response = client.get(
        f"{ws.url}/transactions",
        params={"date_from": "2026-10-01", "date_to": "2026-09-01"},
        headers=ws.owner.headers,
    )

    assert response.status_code == 422


# ── Updating and deleting ─────────────────────────────


def test_updates_are_validated_and_audited(client: TestClient, migrated_database: str) -> None:
    ws = make_workspace(client)
    created = create_transaction(client, ws, amount="1250.50")
    url = f"{ws.url}/transactions/{created['id']}"

    updated = client.patch(
        url, json={"amount": "1300.00", "description": "Revised invoice"}, headers=ws.owner.headers
    )
    null_description = client.patch(url, json={"description": None}, headers=ws.owner.headers)
    # Switching to "expense" while the category is still "Sales" (income) must fail.
    kind_mismatch = client.patch(url, json={"kind": "expense"}, headers=ws.owner.headers)

    assert updated.status_code == 200
    assert Decimal(updated.json()["amount"]) == Decimal("1300")
    assert null_description.status_code == 422
    assert kind_mismatch.status_code == 422
    assert error_field(kind_mismatch.json()) == "category_id"

    events = run_query(
        migrated_database,
        "SELECT details FROM audit_logs WHERE entity_id = :id AND action = 'transaction.updated'",
        id=uuid.UUID(created["id"]),
    )
    changes = events[0]["details"]["changes"]
    assert Decimal(changes["amount"]["old"]) == Decimal("1250.50")
    assert Decimal(changes["amount"]["new"]) == Decimal("1300.00")
    assert changes["description"]["new"] == "Revised invoice"


def test_delete_is_soft_and_audited(client: TestClient, migrated_database: str) -> None:
    ws = make_workspace(client)
    created = create_transaction(client, ws)
    url = f"{ws.url}/transactions/{created['id']}"
    transaction_id = uuid.UUID(created["id"])

    assert client.delete(url, headers=ws.owner.headers).status_code == 204
    assert client.get(url, headers=ws.owner.headers).status_code == 404
    listing = client.get(f"{ws.url}/transactions", headers=ws.owner.headers).json()
    assert listing["total"] == 0
    assert client.delete(url, headers=ws.owner.headers).status_code == 404

    # The row is kept for history, only marked as deleted, and the deletion is audited.
    rows = run_query(
        migrated_database, "SELECT deleted_at FROM transactions WHERE id = :id", id=transaction_id
    )
    events = run_query(
        migrated_database,
        "SELECT action FROM audit_logs WHERE entity_id = :id",
        id=transaction_id,
    )
    assert rows[0]["deleted_at"] is not None
    assert {"transaction.created", "transaction.deleted"} <= {e["action"] for e in events}
