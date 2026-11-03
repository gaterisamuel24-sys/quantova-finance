"""New organizations receive the starter ledger, in their own base currency."""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.defaults import DEFAULT_ACCOUNT_NAME, DEFAULT_CATEGORIES
from tests.helpers import ORGS, create_user, run_query

pytestmark = pytest.mark.integration


@pytest.fixture
def client(integration_settings: Settings, migrated_database: str) -> Iterator[TestClient]:
    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


def test_new_organization_gets_default_account_and_categories(
    client: TestClient, migrated_database: str
) -> None:
    owner = create_user(client)
    response = client.post(
        ORGS,
        json={"name": f"Ledger {uuid.uuid4().hex[:6]}", "base_currency": "KES"},
        headers=owner.headers,
    )
    assert response.status_code == 201
    org_id = uuid.UUID(response.json()["id"])

    accounts = run_query(
        migrated_database,
        "SELECT name, currency FROM financial_accounts WHERE organization_id = :org_id",
        org_id=org_id,
    )
    categories = run_query(
        migrated_database,
        "SELECT name, kind FROM categories WHERE organization_id = :org_id AND is_system",
        org_id=org_id,
    )

    assert accounts == [{"name": DEFAULT_ACCOUNT_NAME, "currency": "KES"}]
    assert {(c["name"], c["kind"]) for c in categories} == {
        (name, kind.value) for name, kind in DEFAULT_CATEGORIES
    }
