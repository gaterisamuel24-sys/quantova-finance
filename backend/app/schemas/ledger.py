"""Request and response bodies for accounts, categories and transactions."""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.enums import AccountType, EntryKind
from app.schemas.money import MoneyAmount

EARLIEST_DATE = date(2000, 1, 1)
MAX_DAYS_AHEAD = 366


def _blank_to_none(value: object) -> object:
    """Optional text fields: an empty or whitespace-only string means "no value"."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _check_occurred_on(value: date) -> date:
    latest = datetime.now(UTC).date() + timedelta(days=MAX_DAYS_AHEAD)
    if not EARLIEST_DATE <= value <= latest:
        raise ValueError(
            f"Date must be between {EARLIEST_DATE.isoformat()} and {latest.isoformat()}"
        )
    return value


Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Counterparty = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Reference = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
OptionalCounterparty = Annotated[Counterparty | None, BeforeValidator(_blank_to_none)]
OptionalReference = Annotated[Reference | None, BeforeValidator(_blank_to_none)]

# Fields a PATCH may omit, but may not set to null.
NON_NULLABLE_ON_UPDATE = frozenset({"kind", "amount", "occurred_on", "account_id", "description"})


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    account_type: AccountType
    currency: str
    opening_balance: Decimal
    is_archived: bool


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    kind: EntryKind
    is_system: bool
    is_archived: bool


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EntryKind
    amount: MoneyAmount
    occurred_on: date
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    description: Description
    counterparty: OptionalCounterparty = None
    reference: OptionalReference = None

    @field_validator("occurred_on")
    @classmethod
    def occurred_on_in_range(cls, value: date) -> date:
        return _check_occurred_on(value)


class TransactionUpdate(BaseModel):
    """Partial update: only fields present in the request are changed."""

    model_config = ConfigDict(extra="forbid")

    kind: EntryKind | None = None
    amount: MoneyAmount | None = None
    occurred_on: date | None = None
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    description: Description | None = None
    counterparty: OptionalCounterparty = None
    reference: OptionalReference = None

    @field_validator("occurred_on")
    @classmethod
    def occurred_on_in_range(cls, value: date | None) -> date | None:
        return None if value is None else _check_occurred_on(value)

    @model_validator(mode="after")
    def reject_nulls_for_required_fields(self) -> Self:
        for field in sorted(self.model_fields_set & NON_NULLABLE_ON_UPDATE):
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: EntryKind
    amount: Decimal
    currency: str
    occurred_on: date
    account_id: uuid.UUID
    category_id: uuid.UUID | None
    description: str
    counterparty: str | None
    reference: str | None
    created_at: datetime
    updated_at: datetime


class TransactionPage(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int
