"""Declarative base and reusable column mixins shared by every ORM model."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import DateTime, MetaData, Numeric, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint names. Without this, PostgreSQL invents names like
# "users_email_key", and Alembic cannot reliably find constraints to alter or drop.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Python type -> database type, applied whenever a model uses Mapped[<type>].
    type_annotation_map: ClassVar[dict[Any, Any]] = {
        # Always timezone-aware: stored as timestamptz, compared in UTC.
        datetime: DateTime(timezone=True),
        # Money: exact decimal with 19 digits, 4 after the point. Never float.
        Decimal: Numeric(19, 4),
    }


class UUIDPrimaryKeyMixin:
    """UUIDv7 primary key: globally unique, unguessable, and ordered by creation time."""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)


class TimestampMixin:
    """created_at / updated_at maintained by the database clock (UTC)."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
