"""Settings as the hosting platform provides them."""

import pytest

from tests.conftest import SettingsFactory


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            "postgres://u:p@db.internal:5432/quantova",
            "postgresql+asyncpg://u:p@db.internal:5432/quantova",
        ),
        ("postgresql://u:p@db.internal/quantova", "postgresql+asyncpg://u:p@db.internal/quantova"),
        (
            "postgresql+asyncpg://u:p@db.internal/quantova",
            "postgresql+asyncpg://u:p@db.internal/quantova",
        ),
    ],
)
def test_platform_database_urls_use_the_async_driver(
    settings_factory: SettingsFactory, given: str, expected: str
) -> None:
    assert settings_factory(database_url=given).database_url.get_secret_value() == expected


def test_render_public_url_is_the_default_base_url(
    settings_factory: SettingsFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://quantova.onrender.com")
    monkeypatch.delenv("APP_BASE_URL", raising=False)

    assert settings_factory().app_base_url == "https://quantova.onrender.com"
    # An explicit APP_BASE_URL (for example a custom domain later) wins.
    assert (
        settings_factory(app_base_url="https://app.quantova.co.ke").app_base_url
        == "https://app.quantova.co.ke"
    )


def test_without_render_the_local_default_applies(
    settings_factory: SettingsFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.delenv("APP_BASE_URL", raising=False)

    assert settings_factory().app_base_url == "http://localhost:5173"
