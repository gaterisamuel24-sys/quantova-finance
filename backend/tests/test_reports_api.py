"""End-to-end tests for report downloads (CSV and PDF)."""

import csv
import io
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.report_export import UTF8_BOM
from tests.helpers import create_user, run_query
from tests.test_analytics_api import MARCH, expense, income
from tests.test_transactions_api import Workspace, make_workspace

pytestmark = pytest.mark.integration


@pytest.fixture
def client(integration_settings: Settings, migrated_database: str) -> Iterator[TestClient]:
    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


def download(client: TestClient, ws: Workspace, report: str, **params: str) -> bytes:
    response = client.get(f"{ws.url}/reports/{report}", params=params, headers=ws.owner.headers)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].startswith("attachment; filename=")
    return response.content


def csv_rows(content: bytes) -> list[list[str]]:
    text = content.decode("utf-8").removeprefix(UTF8_BOM)
    return list(csv.reader(io.StringIO(text)))


def test_transactions_csv_is_exact_and_safe_to_open(client: TestClient) -> None:
    ws = make_workspace(client)
    income(client, ws, "1250.5", "2026-03-02", description='=HYPERLINK("http://evil.example")')
    expense(client, ws, "0.10", "2026-03-05")
    income(client, ws, "99.00", "2026-04-01")  # outside the range

    response = client.get(
        f"{ws.url}/reports/transactions.csv", params=MARCH, headers=ws.owner.headers
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "-transactions-2026-03-01_2026-03-31.csv" in response.headers["content-disposition"]
    header, first, second = csv_rows(response.content)
    assert header[:5] == ["date", "type", "amount", "currency", "description"]
    assert first[:5] == [
        "2026-03-02",
        "income",
        "1250.50",
        "KES",
        '\'=HYPERLINK("http://evil.example")',
    ]
    assert first[5:7] == ["Sales", "Main account"]
    assert second[:3] == ["2026-03-05", "expense", "0.10"]


def test_transactions_csv_can_be_limited_to_one_kind(client: TestClient) -> None:
    ws = make_workspace(client)
    income(client, ws, "10.00", "2026-03-02")
    expense(client, ws, "5.00", "2026-03-03")

    rows = csv_rows(download(client, ws, "transactions.csv", kind="expense", **MARCH))

    assert [row[1] for row in rows[1:]] == ["expense"]


def test_profit_loss_csv_and_pdf(client: TestClient) -> None:
    ws = make_workspace(client)
    income(client, ws, "500.00", "2026-03-02")
    expense(client, ws, "125.00", "2026-03-03")

    rows = csv_rows(download(client, ws, "profit-loss.csv", **MARCH))
    pdf = download(client, ws, "profit-loss.pdf", **MARCH)

    assert ["Result", "Net profit", "375.00", "", ""] in rows
    assert ["Result", "Profit margin", "", "", "75.0%"] in rows
    assert pdf.startswith(b"%PDF-")


def test_cash_flow_csv(client: TestClient) -> None:
    ws = make_workspace(client)
    income(client, ws, "100.00", "2026-01-05")
    expense(client, ws, "30.00", "2026-02-10")

    rows = csv_rows(
        download(
            client,
            ws,
            "cash-flow.csv",
            date_from="2026-01-01",
            date_to="2026-02-28",
            granularity="month",
        )
    )

    assert rows[1] == ["2026-01-01", "2026-01-31", "100.00", "0.00", "100.00", "100.00"]
    assert rows[2] == ["2026-02-01", "2026-02-28", "0.00", "30.00", "-30.00", "70.00"]


def test_every_download_is_audited(client: TestClient, migrated_database: str) -> None:
    ws = make_workspace(client)
    download(client, ws, "profit-loss.pdf", **MARCH)

    # ->> reads JSON fields as text inside PostgreSQL, so no JSON decoding is needed here.
    entries = run_query(
        migrated_database,
        "SELECT details->>'report' AS report, details->>'format' AS format, "
        "details->>'date_from' AS date_from FROM audit_logs "
        "WHERE organization_id = :org_id AND action = 'report.exported'",
        org_id=uuid.UUID(ws.org_id),
    )

    assert entries == [{"report": "profit_loss", "format": "pdf", "date_from": "2026-03-01"}]


def test_non_members_cannot_download(client: TestClient) -> None:
    ws = make_workspace(client)
    outsider = create_user(client)

    for report in ("transactions.csv", "profit-loss.csv", "profit-loss.pdf", "cash-flow.csv"):
        response = client.get(f"{ws.url}/reports/{report}", headers=outsider.headers)
        assert response.status_code == 404, report


def test_rejects_invalid_ranges(client: TestClient) -> None:
    ws = make_workspace(client)

    response = client.get(
        f"{ws.url}/reports/transactions.csv",
        params={"date_from": "2026-03-31", "date_to": "2026-03-01"},
        headers=ws.owner.headers,
    )

    assert response.status_code == 422
