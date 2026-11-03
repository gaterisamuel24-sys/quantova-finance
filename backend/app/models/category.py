"""Categories classify transactions (e.g. "Sales" income, "Rent & utilities" expense)."""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import str_enum_column_type
from app.models.enums import EntryKind


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("organization_id", "kind", "name"),
        # Target of the composite foreign key that forces a transaction's kind to match.
        UniqueConstraint("organization_id", "id", "kind"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[EntryKind] = mapped_column(str_enum_column_type(EntryKind, "category_kind"))
    is_system: Mapped[bool] = mapped_column(default=False, server_default=false())
    is_archived: Mapped[bool] = mapped_column(default=False, server_default=false())
