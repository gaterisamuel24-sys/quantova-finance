"""Unit tests for exact money parsing. No database required."""

from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.money import MoneyAmount


class Payment(BaseModel):
    amount: MoneyAmount


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1250.50", Decimal("1250.50")),
        ("0.0001", Decimal("0.0001")),
        (" 42 ", Decimal("42")),
        (42, Decimal("42")),
        ("999999999999999.9999", Decimal("999999999999999.9999")),
    ],
)
def test_valid_amounts_are_parsed_exactly(raw: object, expected: Decimal) -> None:
    assert Payment.model_validate({"amount": raw}).amount == expected


@pytest.mark.parametrize(
    "raw",
    [
        1250.5,  # JSON float: could already be imprecise
        "1.23456",  # more than 4 decimal places
        "-5",  # direction belongs in `kind`, not the sign
        "0",
        "1e3",  # scientific notation
        "1,250.00",  # thousands separators
        "",
        "abc",
        True,
        "1234567890123456",  # 16 digits before the point
    ],
)
def test_invalid_amounts_are_rejected(raw: object) -> None:
    with pytest.raises(ValidationError):
        Payment.model_validate({"amount": raw})


def test_amounts_serialize_as_exact_strings() -> None:
    payment = Payment.model_validate({"amount": "10.50"})

    assert payment.model_dump(mode="json") == {"amount": "10.50"}
