"""End-to-end tests for the analytics endpoints: summary, cash flow and profit & loss."""

import asyncio
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.main import create_app
from app.services.analytics_math import fiscal_year_start
from tests.helpers import ORGS, create_user
from tests.test_transactions_api import Workspace, create_transaction, error_field, make_workspace

pytestmark = pytest.mark.integration


@pytest.fixture
def client(integration_settings: Settings, migrated_database: str) -> Iterator[TestClient]:
    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


def execute_sql(database_url: str, sql: str, **params: Any) -> None:
    """Run and commit a statement outside the app (to set up data the API cannot)."""

    async def _run() -> None:
        engine = create_async_engine(database_url)
        try:
            async with engine.begin() as connection:
                await connection.execute(text(sql), params)
        finally:
            await engine.dispose()

    asyncio.run(_run())


def get(client: TestClient, ws: Workspace, report: str, **params: str) -> dict[str, Any]:
    response = client.get(f"{ws.url}/analytics/{report}", params=params, headers=ws.owner.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def income(client: TestClient, ws: Workspace, amount: str, on: str, **extra: Any) -> None:
    create_transaction(client, ws, kind="income", amount=amount, occurred_on=on, **extra)


def expense(client: TestClient, ws: Workspace, amount: str, on: str, **extra: Any) -> None:
    create_transaction(
        client,
        ws,
        kind="expense",
        amount=amount,
        occurred_on=on,
        category_id=ws.expense_category_id,
        **extra,
    )


MARCH = {"date_from": "2026-03-01", "date_to": "2026-03-31"}


# ── Summary ───────────────────────────────────────────


def test_summary_sums_exactly_and_compares_with_the_previous_period(client: TestClient) -> None:
    ws = make_workspace(client)
    income(client, ws, "100.00", "2026-02-10")
    income(client, ws, "0.10", "2026-03-02")
    income(client, ws, "0.20", "2026-03-15")
    expense(client, ws, "0.05", "2026-03-20")

    body = get(client, ws, "summary", **MARCH)

    assert body["currency"] == "KES"
    assert body["period"] == {
        "start": "2026-03-01",
        "end": "2026-03-31",
        "days": 31,
        "preset": None,
    }
    # March compares with the whole of February, not "the 31 days before".
    assert body["previous_period"]["start"] == "2026-02-01"
    assert body["previous_period"]["end"] == "2026-02-28"

    current = body["current"]
    assert isinstance(current["income"], str)  # money is sent as a string, never a float
    assert Decimal(current["income"]) == Decimal("0.30")  # exact: no 0.30000000000000004
    assert Decimal(current["expenses"]) == Decimal("0.05")
    assert Decimal(current["net"]) == Decimal("0.25")
    assert current["transaction_count"] == 3
    assert Decimal(body["previous"]["income"]) == Decimal("100")

    assert Decimal(body["change"]["income_pct"]) == Decimal("-99.7")
    assert body["change"]["expenses_pct"] is None  # nothing to compare against


def test_cash_balance_includes_opening_balance_and_earlier_history(
    client: TestClient, migrated_database: str
) -> None:
    ws = make_workspace(client)
    execute_sql(
        migrated_database,
        "UPDATE financial_accounts SET opening_balance = 500 WHERE id = :id",
        id=uuid.UUID(ws.account_id),
    )
    income(client, ws, "200.00", "2026-01-15")
    expense(client, ws, "50.00", "2026-03-10")
    income(client, ws, "1000.00", "2026-04-01")  # after the period: not in the balance

    body = get(client, ws, "summary", **MARCH)

    assert Decimal(body["cash_balance"]) == Decimal("650.00")
    assert body["cash_balance_as_of"] == "2026-03-31"


def test_deleted_and_other_organizations_transactions_are_excluded(client: TestClient) -> None:
    ws = make_workspace(client)
    other = make_workspace(client)
    income(client, other, "999.00", "2026-03-05")
    deleted = create_transaction(client, ws, amount="42.00", occurred_on="2026-03-05")
    response = client.delete(f"{ws.url}/transactions/{deleted['id']}", headers=ws.owner.headers)
    assert response.status_code == 204

    body = get(client, ws, "summary", **MARCH)

    assert Decimal(body["current"]["income"]) == 0
    assert body["current"]["transaction_count"] == 0


def test_transactions_in_another_currency_are_counted_not_summed(client: TestClient) -> None:
    ws = make_workspace(client)
    income(client, ws, "100.00", "2026-03-05")  # recorded in KES
    response = client.patch(ws.url, json={"base_currency": "USD"}, headers=ws.owner.headers)
    assert response.status_code == 200, response.text

    body = get(client, ws, "summary", **MARCH)

    assert body["currency"] == "USD"
    assert Decimal(body["current"]["income"]) == 0  # KES is never added to USD
    assert body["other_currency_transaction_count"] == 1


def test_default_period_is_this_month(client: TestClient) -> None:
    ws = make_workspace(client)
    today = datetime.now(UTC).date()
    income(client, ws, "75.25", today.isoformat())

    body = get(client, ws, "summary")

    assert body["period"]["preset"] == "this_month"
    assert body["period"]["start"] == today.replace(day=1).isoformat()
    assert Decimal(body["current"]["income"]) == Decimal("75.25")


def test_fiscal_periods_follow_the_organization_setting(client: TestClient) -> None:
    ws = make_workspace(client)
    response = client.patch(ws.url, json={"fiscal_year_start_month": 7}, headers=ws.owner.headers)
    assert response.status_code == 200, response.text

    body = get(client, ws, "summary", period="this_fiscal_year")

    expected_start = fiscal_year_start(datetime.now(UTC).date(), 7)
    assert body["period"]["start"] == expected_start.isoformat()
    assert body["period"]["days"] in (365, 366)


# ── Cash flow ─────────────────────────────────────────


def test_monthly_cash_flow_is_zero_filled_with_a_running_balance(client: TestClient) -> None:
    ws = make_workspace(client)
    income(client, ws, "40.00", "2025-12-20")  # before the range: part of the opening balance
    income(client, ws, "100.00", "2026-01-05")
    expense(client, ws, "30.00", "2026-03-31")

    body = get(
        client,
        ws,
        "cash-flow",
        date_from="2026-01-01",
        date_to="2026-04-30",
        granularity="month",
    )

    assert Decimal(body["opening_balance"]) == Decimal("40.00")
    points = body["points"]
    assert [p["start"] for p in points] == ["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"]
    assert Decimal(points[1]["income"]) == 0  # February had nothing, but still appears
    assert [Decimal(p["closing_balance"]) for p in points] == [
        Decimal("140.00"),
        Decimal("140.00"),
        Decimal("110.00"),
        Decimal("110.00"),
    ]
    assert Decimal(body["closing_balance"]) == Decimal("110.00")


def test_weekly_points_are_clipped_to_the_range(client: TestClient) -> None:
    ws = make_workspace(client)

    # Wednesday 4 March to Tuesday 17 March 2026.
    body = get(
        client, ws, "cash-flow", date_from="2026-03-04", date_to="2026-03-17", granularity="week"
    )

    assert [(p["start"], p["end"]) for p in body["points"]] == [
        ("2026-03-04", "2026-03-08"),
        ("2026-03-09", "2026-03-15"),
        ("2026-03-16", "2026-03-17"),
    ]


def test_cash_flow_rejects_too_many_points(client: TestClient) -> None:
    ws = make_workspace(client)

    response = client.get(
        f"{ws.url}/analytics/cash-flow",
        params={"date_from": "2020-01-01", "date_to": "2026-01-01", "granularity": "day"},
        headers=ws.owner.headers,
    )

    assert response.status_code == 422
    assert error_field(response.json()) == "granularity"


# ── Profit & loss ─────────────────────────────────────


def test_profit_and_loss_groups_by_category(client: TestClient) -> None:
    ws = make_workspace(client)
    income(client, ws, "300.00", "2026-03-01")
    income(client, ws, "100.00", "2026-03-02")
    income(client, ws, "100.00", "2026-03-03", category_id=None)
    expense(client, ws, "125.00", "2026-03-04")

    body = get(client, ws, "profit-loss", **MARCH)

    income_lines = [
        (line["name"], Decimal(line["amount"]), line["transaction_count"], line["share_pct"])
        for line in body["income"]["lines"]
    ]
    assert income_lines == [
        ("Sales", Decimal("400.00"), 2, "80.0"),
        ("Uncategorized", Decimal("100.00"), 1, "20.0"),
    ]
    assert body["income"]["lines"][1]["category_id"] is None
    assert Decimal(body["income"]["total"]) == Decimal("500.00")
    assert [line["name"] for line in body["expenses"]["lines"]] == ["Rent & utilities"]
    assert Decimal(body["expenses"]["total"]) == Decimal("125.00")
    assert Decimal(body["net_profit"]) == Decimal("375.00")
    assert body["margin_pct"] == "75.0"


def test_profit_and_loss_without_income_has_no_margin(client: TestClient) -> None:
    ws = make_workspace(client)
    expense(client, ws, "10.00", "2026-03-04")

    body = get(client, ws, "profit-loss", **MARCH)

    assert Decimal(body["net_profit"]) == Decimal("-10.00")
    assert body["margin_pct"] is None


# ── Validation and access ─────────────────────────────


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"period": "this_month", "date_from": "2026-03-01", "date_to": "2026-03-31"}, "period"),
        ({"date_from": "2026-03-01"}, "date_to"),
        ({"date_from": "2026-03-31", "date_to": "2026-03-01"}, "date_from"),
        ({"date_from": "2000-01-01", "date_to": "2026-01-01"}, "date_to"),
        ({"period": "next_century"}, "period"),
    ],
)
def test_rejects_invalid_ranges(client: TestClient, params: dict[str, str], field: str) -> None:
    ws = make_workspace(client)

    response = client.get(f"{ws.url}/analytics/summary", params=params, headers=ws.owner.headers)

    assert response.status_code == 422
    assert error_field(response.json()) == field


def test_non_members_cannot_read_analytics(client: TestClient) -> None:
    ws = make_workspace(client)
    outsider = create_user(client)

    for report in ("summary", "cash-flow", "profit-loss"):
        response = client.get(f"{ws.url}/analytics/{report}", headers=outsider.headers)
        assert response.status_code == 404, report


def test_analytics_require_authentication(client: TestClient) -> None:
    ws = make_workspace(client)
    response = client.get(f"{ORGS}/{ws.org_id}/analytics/summary")
    assert response.status_code == 401
