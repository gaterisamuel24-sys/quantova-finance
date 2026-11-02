"""Organizations (workspaces): the tenant boundary. All financial data belongs to one."""

from sqlalchemy import CHAR, CheckConstraint, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("base_currency ~ '^[A-Z]{3}$'", name="base_currency_iso4217"),
        CheckConstraint(
            "fiscal_year_start_month BETWEEN 1 AND 12", name="fiscal_year_start_month_range"
        ),
        CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="slug_format"),
    )

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    base_currency: Mapped[str] = mapped_column(CHAR(3), default="USD", server_default="USD")
    fiscal_year_start_month: Mapped[int] = mapped_column(
        SmallInteger, default=1, server_default="1"
    )
