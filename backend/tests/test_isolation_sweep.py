"""Tenant isolation, checked for every organization endpoint at once.

Every route whose path contains {org_id} is called by a signed-in user who is NOT a
member of that organization, with every method it accepts. Each call must answer 404
(as if the organization did not exist) and must change nothing.

The routes are discovered automatically, so an endpoint added later is covered without
anyone remembering to write a test for it. A second test makes sure no API module is
missed by the discovery itself.
"""

import importlib
import pkgutil
import re
import uuid
from collections.abc import Iterator
from types import ModuleType

import pytest
from fastapi import APIRouter
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import app.api.v1 as api_v1
from app.core.config import Settings
from app.main import create_app
from tests.helpers import create_user, run_query
from tests.test_transactions_api import create_transaction, make_workspace

pytestmark = pytest.mark.integration

API_PREFIX = "/api/v1"
PATH_PARAM = re.compile(r"\{([^}]+)\}")


def api_modules() -> list[ModuleType]:
    """Every module in app/api/v1 that defines a router."""
    modules = []
    for info in pkgutil.iter_modules(api_v1.__path__):
        module = importlib.import_module(f"{api_v1.__name__}.{info.name}")
        if isinstance(getattr(module, "router", None), APIRouter) and info.name != "router":
            modules.append(module)
    return modules


def organization_routes() -> list[tuple[str, str]]:
    """(method, path) for every route that belongs to one organization."""
    routes: list[tuple[str, str]] = []
    for module in api_modules():
        for route in module.router.routes:
            if isinstance(route, APIRoute) and "{org_id}" in route.path:
                routes.extend((method, route.path) for method in sorted(route.methods or ()))
    return sorted(set(routes))


def test_discovery_finds_the_organization_api() -> None:
    found = {path for _, path in organization_routes()}

    # A sample from each area: if any is missing, discovery is broken, not the API.
    for expected in (
        "/orgs/{org_id}",
        "/orgs/{org_id}/members",
        "/orgs/{org_id}/transactions",
        "/orgs/{org_id}/transactions/import",
        "/orgs/{org_id}/analytics/summary",
        "/orgs/{org_id}/reports/transactions.csv",
        "/orgs/{org_id}/insights",
        "/orgs/{org_id}/billing",
    ):
        assert expected in found, f"{expected} was not discovered"


@pytest.fixture
def client(integration_settings: Settings, migrated_database: str) -> Iterator[TestClient]:
    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


def fill(path: str, org_id: str) -> str:
    """The victim organization's real id; random ids for anything else in the path."""
    return API_PREFIX + PATH_PARAM.sub(
        lambda match: org_id if match.group(1) == "org_id" else str(uuid.uuid4()), path
    )


def test_outsiders_get_404_from_every_organization_endpoint(
    client: TestClient, migrated_database: str
) -> None:
    victim = make_workspace(client)
    create_transaction(client, victim)  # so there is something that could leak
    outsider = create_user(client)
    before = run_query(
        migrated_database,
        "SELECT (SELECT count(*) FROM transactions WHERE organization_id = :org_id) AS tx, "
        "(SELECT count(*) FROM memberships WHERE organization_id = :org_id) AS members",
        org_id=uuid.UUID(victim.org_id),
    )

    leaks = []
    for method, path in organization_routes():
        url = fill(path, victim.org_id)
        body: dict[str, object] | None = {} if method in {"POST", "PUT", "PATCH"} else None
        response = client.request(method, url, json=body, headers=outsider.headers)
        if response.status_code != 404:
            leaks.append(f"{method} {path} -> {response.status_code}")

    assert leaks == [], "Endpoints that did not hide another organization:\n" + "\n".join(leaks)
    after = run_query(
        migrated_database,
        "SELECT (SELECT count(*) FROM transactions WHERE organization_id = :org_id) AS tx, "
        "(SELECT count(*) FROM memberships WHERE organization_id = :org_id) AS members",
        org_id=uuid.UUID(victim.org_id),
    )
    assert after == before  # nothing was changed or deleted


def test_signed_out_requests_get_401_everywhere(client: TestClient) -> None:
    victim = make_workspace(client)

    wrong = []
    for method, path in organization_routes():
        response = client.request(method, fill(path, victim.org_id))
        if response.status_code != 401:
            wrong.append(f"{method} {path} -> {response.status_code}")

    assert wrong == [], "Endpoints reachable without signing in:\n" + "\n".join(wrong)
