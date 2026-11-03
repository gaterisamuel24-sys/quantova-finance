"""End-to-end tests for CSV import: all-or-nothing, dry runs, limits and permissions."""

import uuid
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.csv_import import MAX_IMPORT_BYTES
from tests.helpers import create_user, run_query
from tests.test_transactions_api import Workspace, make_workspace

pytestmark = pytest.mark.integration

GOOD_CSV = (
    "date,type,amount,description,category\n"
    "2026-10-01,income,1250.50,Invoice 1042,Sales\n"
    "2026-10-03,expense,320.00,October rent,Rent & utilities\n"
    "2026-10-05,income,99.99,Small sale,\n"
)
BAD_CSV = GOOD_CSV + "2026-10-06,expense,abc,Broken row,\n"


@pytest.fixture
def client(integration_settings: Settings, migrated_database: str) -> Iterator[TestClient]:
    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


def upload(
    client: TestClient, ws: Workspace, content: str | bytes, *, dry_run: bool = False
) -> Any:
    data = content.encode() if isinstance(content, str) else content
    return client.post(
        f"{ws.url}/transactions/import",
        params={"dry_run": str(dry_run).lower()},
        files={"file": ("transactions.csv", data, "text/csv")},
        headers=ws.owner.headers,
    )


def transaction_count(client: TestClient, ws: Workspace) -> int:
    listing = client.get(f"{ws.url}/transactions", headers=ws.owner.headers).json()
    total: int = listing["total"]
    return total


def test_imports_every_row_and_audits_the_import(
    client: TestClient, migrated_database: str
) -> None:
    ws = make_workspace(client)

    response = upload(client, ws, GOOD_CSV)

    assert response.status_code == 200
    report = response.json()
    assert (report["status"], report["imported_count"], report["error_count"]) == (
        "imported",
        3,
        0,
    )
    assert transaction_count(client, ws) == 3
    events = run_query(
        migrated_database,
        "SELECT details FROM audit_logs "
        "WHERE organization_id = :org AND action = 'transaction.imported'",
        org=uuid.UUID(ws.org_id),
    )
    assert events[0]["details"]["rows"] == 3
    assert Decimal(events[0]["details"]["income_total"]) == Decimal("1350.49")
    assert Decimal(events[0]["details"]["expense_total"]) == Decimal("320.00")


def test_one_bad_row_rejects_the_whole_file(client: TestClient) -> None:
    ws = make_workspace(client)

    report = upload(client, ws, BAD_CSV).json()

    assert report["status"] == "rejected"
    assert report["imported_count"] == 0
    assert [(e["row"], e["column"]) for e in report["errors"]] == [(5, "amount")]
    assert transaction_count(client, ws) == 0  # nothing was imported


def test_dry_run_validates_without_importing(client: TestClient) -> None:
    ws = make_workspace(client)

    report = upload(client, ws, GOOD_CSV, dry_run=True).json()

    assert report["status"] == "validated"
    assert report["row_count"] == 3
    assert transaction_count(client, ws) == 0


@pytest.mark.parametrize(
    "content",
    [
        "date,type,amount\n2026-10-01,income,1\n",  # missing a required column
        "date,type,amount,description\n2026-10-01,income,1,Caf\xe9\n".encode("cp1252"),
    ],
)
def test_unusable_files_get_a_clear_400(client: TestClient, content: str | bytes) -> None:
    ws = make_workspace(client)

    response = upload(client, ws, content)

    assert response.status_code == 400
    assert response.json()["detail"]


def test_rejects_files_over_the_size_limit(client: TestClient) -> None:
    ws = make_workspace(client)

    response = upload(client, ws, b"x" * (MAX_IMPORT_BYTES + 1))

    assert response.status_code == 413


def test_viewers_can_download_the_template_but_not_import(client: TestClient) -> None:
    ws = make_workspace(client)
    viewer = create_user(client)
    client.post(
        f"{ws.url}/members",
        json={"email": viewer.email, "role": "viewer"},
        headers=ws.owner.headers,
    )

    template = client.get(f"{ws.url}/transactions/import/template", headers=viewer.headers)
    blocked = client.post(
        f"{ws.url}/transactions/import",
        files={"file": ("t.csv", GOOD_CSV.encode(), "text/csv")},
        headers=viewer.headers,
    )

    assert template.status_code == 200
    assert template.text.startswith("date,type,amount,description")
    assert "attachment" in template.headers["content-disposition"]
    assert blocked.status_code == 403
