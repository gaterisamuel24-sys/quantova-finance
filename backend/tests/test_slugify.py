"""Unit tests for organization slug generation."""

import pytest

from app.services.organizations import slugify


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Acme Ltd", "acme-ltd"),
        ("  Café Ünïcode & Co.  ", "cafe-unicode-co"),
        ("Nairobi Traders 2026", "nairobi-traders-2026"),
        ("!!!", "org"),
    ],
)
def test_slugify(name: str, expected: str) -> None:
    assert slugify(name) == expected
