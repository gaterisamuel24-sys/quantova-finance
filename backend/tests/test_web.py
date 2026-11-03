"""Serving the built frontend from the API (production), with the right headers."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import SettingsFactory

FRONTEND_CSP = "default-src 'self'; script-src 'self'; object-src 'none'"


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    """A miniature frontend build, laid out like Vite's output."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    (tmp_path / "assets" / "app-3f2a.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "theme-init.js").write_text("(function(){})()", encoding="utf-8")
    (tmp_path / "content-security-policy.txt").write_text(FRONTEND_CSP + "\n", encoding="utf-8")
    (tmp_path.parent / "secret.txt").write_text("do not serve", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(settings_factory: SettingsFactory, dist: Path) -> Iterator[TestClient]:
    app = create_app(settings_factory(frontend_dist_dir=str(dist)))
    with TestClient(app) as test_client:
        yield test_client


def test_the_app_is_served_with_its_own_security_policy(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "<div id=root>" in response.text
    assert response.headers["content-security-policy"] == f"{FRONTEND_CSP}; frame-ancestors 'none'"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-frame-options"] == "DENY"


def test_app_routes_fall_back_to_index_html(client: TestClient) -> None:
    response = client.get("/app/0193f2a0-1111-7000-8000-000000000001/transactions?page=2")

    assert response.status_code == 200
    assert "<div id=root>" in response.text


def test_hashed_assets_are_cached_for_a_year(client: TestClient) -> None:
    asset = client.get("/assets/app-3f2a.js")
    script = client.get("/theme-init.js")

    assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert script.headers["cache-control"] == "no-cache"  # not content-hashed


def test_the_api_keeps_its_strict_policy_and_json_404s(client: TestClient) -> None:
    health = client.get("/api/v1/health")
    unknown = client.get("/api/v1/does-not-exist")

    assert health.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert health.headers["cache-control"] == "no-store"
    assert unknown.status_code == 404
    assert unknown.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize(
    "path",
    [
        "/../secret.txt",
        "/%2e%2e/secret.txt",
        "/assets/../../secret.txt",
        "/content-security-policy.txt",
    ],
)
def test_files_outside_the_app_are_never_served(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert "do not serve" not in response.text
    assert FRONTEND_CSP not in response.text


def test_without_a_build_only_the_api_is_served(settings_factory: SettingsFactory) -> None:
    with TestClient(create_app(settings_factory())) as client:
        assert client.get("/").status_code == 404
        assert client.get("/api/v1/health").status_code == 200
