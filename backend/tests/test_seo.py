"""robots.txt and sitemap.xml: production is findable, other servers are not."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import SettingsFactory

BASE = "https://quantova.example"


@pytest.fixture(autouse=True)
def no_render_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.delenv("APP_BASE_URL", raising=False)


def test_production_lists_the_public_pages(settings_factory: SettingsFactory) -> None:
    settings = settings_factory(environment="production", app_base_url=BASE)
    with TestClient(create_app(settings)) as client:
        robots = client.get("/robots.txt")
        sitemap = client.get("/sitemap.xml")

    assert robots.status_code == 200
    assert robots.headers["content-type"].startswith("text/plain")
    assert "Disallow: /app\n" in robots.text
    assert "Disallow: /api/\n" in robots.text
    assert f"Sitemap: {BASE}/sitemap.xml" in robots.text

    assert sitemap.status_code == 200
    assert sitemap.headers["content-type"].startswith("application/xml")
    assert f"<loc>{BASE}/guide</loc>" in sitemap.text
    assert "/app" not in sitemap.text


def test_other_servers_ask_not_to_be_indexed(settings_factory: SettingsFactory) -> None:
    for environment in ("development", "staging"):
        with TestClient(create_app(settings_factory(environment=environment))) as client:
            assert client.get("/robots.txt").text == "User-agent: *\nDisallow: /\n"
