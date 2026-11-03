"""End-to-end tests for AI insights, with a fake model in place of OpenAI."""

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api.v1.insights import get_insight_model
from app.core.config import Settings
from app.main import create_app
from app.services.insights.explain import InsightOutput, Observation
from tests.fake_ai import FakeInsightModel
from tests.helpers import ORGS, create_user, run_query
from tests.test_transactions_api import Workspace, create_transaction, make_workspace

pytestmark = pytest.mark.integration

TODAY = datetime.now(UTC).date().isoformat()


def grounded_answer(output_type: type[BaseModel], input_text: str) -> BaseModel:
    """A well-behaved model: it only quotes figures from the snapshot it was given."""
    assert output_type is InsightOutput
    snapshot = json.loads(input_text.split("\n\n")[0])
    income = next(fact for fact in snapshot["facts"] if fact["id"] == "income")
    return InsightOutput(
        headline=f"Income this period was {snapshot['currency']} {income['value']}.",
        observations=[
            Observation(
                title="Income recorded",
                detail=f"You recorded {snapshot['currency']} {income['value']} of income.",
                kind="neutral",
                fact_ids=["income"],
            )
        ],
        suggestions=[],
    )


def build_client(settings: Settings, model: FakeInsightModel | None) -> Iterator[TestClient]:
    app: FastAPI = create_app(settings)
    if model is not None:
        app.dependency_overrides[get_insight_model] = lambda: model
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def model() -> FakeInsightModel:
    return FakeInsightModel(respond=grounded_answer)


@pytest.fixture
def client(
    integration_settings: Settings, migrated_database: str, model: FakeInsightModel
) -> Iterator[TestClient]:
    yield from build_client(integration_settings, model)


def generate(client: TestClient, ws: Workspace, **body: str) -> dict[str, Any]:
    response = client.post(f"{ws.url}/insights", json=body, headers=ws.owner.headers)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def test_generates_stores_and_lists_an_insight(client: TestClient, migrated_database: str) -> None:
    ws = make_workspace(client)
    create_transaction(client, ws, amount="1250.50", occurred_on=TODAY)

    created = generate(client, ws)

    assert created["headline"] == "Income this period was KES 1250.5000."
    assert created["model"] == "fake-model"
    assert created["period_preset"] == "this_month"
    facts = {fact["id"]: fact for fact in created["facts"]}
    assert facts["income"]["value"] == "1250.5000"  # exact, as a string

    listed = client.get(f"{ws.url}/insights", headers=ws.owner.headers).json()
    assert [item["id"] for item in listed["items"]] == [created["id"]]
    assert listed["remaining_today"] == listed["daily_limit"] - 1

    audit = run_query(
        migrated_database,
        "SELECT details->>'model' AS model, details->>'input_tokens' AS input_tokens "
        "FROM audit_logs WHERE organization_id = :org_id AND action = 'insight.generated'",
        org_id=uuid.UUID(ws.org_id),
    )
    assert audit == [{"model": "fake-model", "input_tokens": "100"}]


def test_sends_totals_only(client: TestClient, model: FakeInsightModel) -> None:
    ws = make_workspace(client)
    create_transaction(
        client,
        ws,
        occurred_on=TODAY,
        description="Private note about client SECRET-DESCRIPTION",
        counterparty="Confidential Customer Ltd",
        reference="INV-SECRET-42",
    )

    generate(client, ws)

    sent = str(model.calls[0]["input_text"])
    for private in ("SECRET-DESCRIPTION", "Confidential Customer", "INV-SECRET-42", ws.org_id):
        assert private not in sent
    assert ws.owner.headers["Authorization"].split()[1] not in sent


def test_a_period_without_transactions_is_refused(
    client: TestClient, model: FakeInsightModel
) -> None:
    ws = make_workspace(client)

    response = client.post(f"{ws.url}/insights", json={}, headers=ws.owner.headers)

    assert response.status_code == 422
    assert model.calls == []  # the AI service was never called


def test_daily_limit_per_organization(
    integration_settings: Settings, migrated_database: str, model: FakeInsightModel
) -> None:
    settings = integration_settings.model_copy(update={"ai_daily_insights_per_org": 1})
    for client in build_client(settings, model):
        ws = make_workspace(client)
        create_transaction(client, ws, occurred_on=TODAY)
        generate(client, ws)

        second = client.post(f"{ws.url}/insights", json={}, headers=ws.owner.headers)

        assert second.status_code == 429
        assert len(model.calls) == 1


def test_provider_failure_is_reported_audited_and_not_stored(
    integration_settings: Settings, migrated_database: str
) -> None:
    for client in build_client(integration_settings, FakeInsightModel(fail=True)):
        ws = make_workspace(client)
        create_transaction(client, ws, occurred_on=TODAY)

        response = client.post(f"{ws.url}/insights", json={}, headers=ws.owner.headers)

        assert response.status_code == 502
        assert "unavailable" in response.json()["detail"]
        listed = client.get(f"{ws.url}/insights", headers=ws.owner.headers).json()
        assert listed["items"] == []
        failures = run_query(
            migrated_database,
            "SELECT action FROM audit_logs WHERE organization_id = :org_id "
            "AND action = 'insight.failed'",
            org_id=uuid.UUID(ws.org_id),
        )
        assert len(failures) == 1


def test_without_an_api_key_generation_is_unavailable(
    integration_settings: Settings, migrated_database: str
) -> None:
    settings = integration_settings.model_copy(update={"openai_api_key": None})
    for client in build_client(settings, None):
        ws = make_workspace(client)
        create_transaction(client, ws, occurred_on=TODAY)

        response = client.post(f"{ws.url}/insights", json={}, headers=ws.owner.headers)
        listed = client.get(f"{ws.url}/insights", headers=ws.owner.headers)

        assert response.status_code == 503
        assert listed.json()["ai_enabled"] is False


def test_viewers_can_read_but_not_generate(client: TestClient) -> None:
    ws = make_workspace(client)
    create_transaction(client, ws, occurred_on=TODAY)
    created = generate(client, ws)
    viewer = create_user(client)
    added = client.post(
        f"{ws.url}/members",
        json={"email": viewer.email, "role": "viewer"},
        headers=ws.owner.headers,
    )
    assert added.status_code == 201

    refused = client.post(f"{ws.url}/insights", json={}, headers=viewer.headers)
    read = client.get(f"{ws.url}/insights/{created['id']}", headers=viewer.headers)

    assert refused.status_code == 403
    assert read.status_code == 200


def test_insights_are_private_to_their_organization(client: TestClient) -> None:
    ws = make_workspace(client)
    create_transaction(client, ws, occurred_on=TODAY)
    created = generate(client, ws)
    other = make_workspace(client)

    # Another organization's member cannot list or open it, even with its id.
    assert client.get(f"{ws.url}/insights", headers=other.owner.headers).status_code == 404
    response = client.get(f"{other.url}/insights/{created['id']}", headers=other.owner.headers)
    assert response.status_code == 404
    assert client.get(f"{ORGS}/{ws.org_id}/insights").status_code == 401


def test_rejects_unknown_fields(client: TestClient) -> None:
    ws = make_workspace(client)

    response = client.post(
        f"{ws.url}/insights",
        json={"period": "this_month", "model": "gpt-x"},
        headers=ws.owner.headers,
    )

    assert response.status_code == 422
