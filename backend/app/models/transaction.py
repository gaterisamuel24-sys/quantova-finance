"""Transactions: every movement of money in or out of an organization's accounts."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CHAR, CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import str_enum_column_type
from app.models.enums import EntryKind


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # Direction is carried by `kind`; amounts are always positive.
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso4217"),
        # Tenant safety: the account must belong to the SAME organization as the transaction.
        ForeignKeyConstraint(
            ["organization_id", "account_id"],
            ["financial_accounts.organization_id", "financial_accounts.id"],
        ),
        # Same organization, and the category's kind must equal the transaction's kind.
        # (Not enforced when category_id is NULL, i.e. "uncategorized".)
        ForeignKeyConstraint(
            ["organization_id", "category_id", "kind"],
            ["categories.organization_id", "categories.id", "categories.kind"],
        ),
        Index("ix_transactions_organization_id_occurred_on", "organization_id", "occurred_on"),
        Index("ix_transactions_organization_id_account_id", "organization_id", "account_id"),
        Index("ix_transactions_organization_id_category_id", "organization_id", "category_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    account_id: Mapped[uuid.UUID]
    category_id: Mapped[uuid.UUID | None]
    kind: Mapped[EntryKind] = mapped_column(str_enum_column_type(EntryKind, "transaction_kind"))
    amount: Mapped[Decimal]
    currency: Mapped[str] = mapped_column(CHAR(3))
    occurred_on: Mapped[date]
    description: Mapped[str] = mapped_column(String(500))
    counterparty: Mapped[str | None] = mapped_column(String(200))
    reference: Mapped[str | None] = mapped_column(String(100))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    deleted_at: Mapped[datetime | None]
