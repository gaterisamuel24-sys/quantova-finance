"""User accounts. Identity only: no financial data lives on this table."""

from datetime import datetime

from sqlalchemy import CheckConstraint, String, false, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import str_enum_column_type
from app.models.enums import PlatformRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        # Emails are normalized to lowercase by the app; the database guarantees it,
        # so "Alice@x.com" and "alice@x.com" can never become two separate accounts.
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    is_email_verified: Mapped[bool] = mapped_column(default=False, server_default=false())
    platform_role: Mapped[PlatformRole] = mapped_column(
        str_enum_column_type(PlatformRole, "platform_role"),
        default=PlatformRole.USER,
        server_default=PlatformRole.USER.value,
    )
    last_login_at: Mapped[datetime | None]
