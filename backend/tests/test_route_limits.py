"""Per-user rate limits: which routes carry them, and that they really stop a burst."""

from collections.abc import Iterator

import pytest
from fastapi import APIRouter
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api.limits import CHECKOUT_PER_USER
from app.api.v1 import billing, imports, insights, organizations, reports
from app.api.v1.billing import get_billing_provider
from app.core.config import Settings
from app.main import create_app
from tests.fake_billing import FakeBillingProvider
from tests.test_transactions_api import make_workspace

ORG = "/orgs/{org_id}"  # paths as each module's router declares them (below /api/v1)

EXPECTED = {
    ("POST", f"{ORG}/insights"): "ai-insights-user",
    ("POST", f"{ORG}/billing/checkout"): "billing-checkout-user",
    ("POST", f"{ORG}/billing/portal"): "billing-portal-user",
    ("POST", f"{ORG}/transactions/import"): "imports-user",
    ("GET", f"{ORG}/reports/transactions.csv"): "exports-user",
    ("GET", f"{ORG}/reports/profit-loss.csv"): "exports-user",
    ("GET", f"{ORG}/reports/profit-loss.pdf"): "exports-user",
    ("GET", f"{ORG}/reports/cash-flow.csv"): "exports-user",
    ("POST", f"{ORG}/members"): "member-invites-user",
}


def route_limits(*routers: APIRouter) -> dict[tuple[str, str], str]:
    """Every route's rate limit, read from the dependencies the route declares.

    Each module's own router is read (rather than the assembled app), because newer
    FastAPI versions keep included routers nested instead of copying their routes.
    """
    found: dict[tuple[str, str], str] = {}
    for router in routers:
        # Router-wide dependencies (as on the reports router) apply to all of its routes.
        router_calls: list[object] = [depends.dependency for depends in router.dependencies]
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            calls = list(router_calls)
            calls += [depends.dependency for depends in route.dependencies]
            calls += [dependency.call for dependency in route.dependant.dependencies]
            for call in calls:
                rule = getattr(call, "rate_limit", None)
                if rule is not None:
                    for method in route.methods or ():
                        found[(method, route.path)] = rule.name
    return found


def test_sensitive_routes_are_rate_limited() -> None:
    found = route_limits(
        insights.router, billing.router, imports.router, reports.router, organizations.router
    )

    missing = {key: rule for key, rule in EXPECTED.items() if found.get(key) != rule}
    assert missing == {}, f"Routes without their rate limit: {missing}. Found: {found}"


@pytest.fixture
def clients(
    integration_settings: Settings, migrated_database: str
) -> Iterator[tuple[TestClient, TestClient]]:
    """Two apps on the same database: one without rate limits (for setting up users, so
    the login and registration limits are not involved), and one with them switched on."""
    limited_settings = integration_settings.model_copy(update={"rate_limit_enabled": True})
    limited_app = create_app(limited_settings)
    # A function, not the class: FastAPI would treat a dataclass's fields as parameters.
    limited_app.dependency_overrides[get_billing_provider] = lambda: FakeBillingProvider()
    with TestClient(create_app(integration_settings)) as setup, TestClient(limited_app) as limited:
        yield setup, limited


@pytest.mark.integration
def test_a_burst_is_stopped_with_retry_after(clients: tuple[TestClient, TestClient]) -> None:
    setup, limited = clients
    ws = make_workspace(setup)

    statuses = []
    for _ in range(CHECKOUT_PER_USER.limit + 1):
        response = limited.post(
            f"{ws.url}/billing/checkout", json={"plan": "pro"}, headers=ws.owner.headers
        )
        statuses.append(response.status_code)

    assert statuses[:-1] == [200] * CHECKOUT_PER_USER.limit
    assert statuses[-1] == 429
    assert int(response.headers["retry-after"]) > 0
