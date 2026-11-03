"""Financial accounts: where an organization's money is held."""

import uuid
from decimal import Decimal

from sqlalchemy import CHAR, CheckConstraint, ForeignKey, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import str_enum_column_type
from app.models.enums import AccountType


class FinancialAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "financial_accounts"
    __table_args__ = (
        UniqueConstraint("organization_id", "name"),
        # Target of the tenant-safe composite foreign key from transactions.
        UniqueConstraint("organization_id", "id"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso4217"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(120))
    account_type: Mapped[AccountType] = mapped_column(
        str_enum_column_type(AccountType, "account_type")
    )
    currency: Mapped[str] = mapped_column(CHAR(3))
    opening_balance: Mapped[Decimal] = mapped_column(default=Decimal("0"), server_default="0")
    is_archived: Mapped[bool] = mapped_column(default=False, server_default=false())
