"""Every payment-provider webhook event we have accepted, recorded once.

The unique (provider, event_id) pair makes processing idempotent: providers retry
deliveries, sometimes more than once, and a repeated event must never be applied
twice. Rows are kept as a record of what the provider told us and when.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class BillingEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "billing_events"
    __table_args__ = (UniqueConstraint("provider", "event_id"),)

    received_at: Mapped[datetime] = mapped_column(server_default=func.now())
    provider: Mapped[str] = mapped_column(String(20))
    event_id: Mapped[str] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(100))
    # "applied", "ignored" or "stale" (an older event arriving after a newer one).
    outcome: Mapped[str] = mapped_column(String(20))
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
