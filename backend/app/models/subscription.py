"""An organization's subscription, as last reported by the payment provider.

At most one row per organization. No row means the organization is on the Free plan.
The provider is the source of truth for payments: this table is updated only from
its verified webhooks (step 6.3), never directly from the browser.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import str_enum_column_type
from app.services.billing.plans import PlanId, SubscriptionStatus


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), unique=True
    )
    plan: Mapped[PlanId] = mapped_column(str_enum_column_type(PlanId, "subscription_plan"))
    status: Mapped[SubscriptionStatus] = mapped_column(
        str_enum_column_type(SubscriptionStatus, "subscription_status")
    )
    provider: Mapped[str] = mapped_column(String(20))
    # The provider's own ids: never secrets, but never shown to other organizations either.
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    current_period_end: Mapped[datetime | None]
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False, server_default=false())
    # When the provider produced the event we last applied. Webhooks can arrive out of
    # order; an event older than this is ignored, so a stale "active" never undoes "canceled".
    provider_updated_at: Mapped[datetime | None]
