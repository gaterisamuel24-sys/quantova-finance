"""Exact money values for the API.

Amounts travel as JSON strings ("1250.50") and are parsed straight into Decimal.
JSON floating-point numbers are rejected: a value such as 0.1 has no exact binary
representation, and financial data must never be silently rounded on the way in.
"""

import re
from decimal import Decimal
from typing import Annotated

from pydantic import BeforeValidator, Field

MAX_INTEGER_DIGITS = 15
MAX_DECIMAL_PLACES = 4

_AMOUNT_PATTERN = re.compile(rf"\d{{1,{MAX_INTEGER_DIGITS}}}(\.\d{{1,{MAX_DECIMAL_PLACES}}})?")


def parse_amount(value: object) -> object:
    """Turn an incoming amount into Decimal, or explain clearly why it is not acceptable."""
    if isinstance(value, bool):
        raise ValueError('Amount must be a number written as a string, e.g. "1250.50"')
    if isinstance(value, float):
        raise ValueError('Send amounts as strings (e.g. "1250.50"), not floating-point numbers')
    if isinstance(value, int):
        value = str(value)
    if isinstance(value, str):
        text = value.strip()
        if not _AMOUNT_PATTERN.fullmatch(text):
            raise ValueError(
                "Amount must be a positive number with at most "
                f"{MAX_DECIMAL_PLACES} decimal places, e.g. 1250.50"
            )
        return Decimal(text)
    return value


MoneyAmount = Annotated[
    Decimal,
    BeforeValidator(parse_amount),
    Field(
        gt=0, max_digits=MAX_INTEGER_DIGITS + MAX_DECIMAL_PLACES, decimal_places=MAX_DECIMAL_PLACES
    ),
]
