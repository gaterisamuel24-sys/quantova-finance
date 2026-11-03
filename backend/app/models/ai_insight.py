"""AI insights: each row is one checked explanation of an organization's figures.

Rows are never edited. Each keeps the exact snapshot the model saw and the answer it
gave, so any insight can be traced back to its inputs, and the model and token
counts, so AI usage and cost can be reviewed.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import CHAR, CheckConstraint, ForeignKey, Index, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class AIInsight(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_insights"
    __table_args__ = (
        CheckConstraint("input_tokens >= 0 AND output_tokens >= 0", name="tokens_non_negative"),
        CheckConstraint("period_start <= period_end", name="period_ordered"),
        # Listing an organization's insights newest first, and counting today's.
        Index("ix_ai_insights_organization_id_created_at", "organization_id", "created_at"),
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    period_start: Mapped[date]
    period_end: Mapped[date]
    period_preset: Mapped[str | None] = mapped_column(String(30))
    currency: Mapped[str] = mapped_column(CHAR(3))
    # The facts sent to the model, and its validated answer, as JSON.
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    output: Mapped[dict[str, Any]] = mapped_column(JSONB)
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int]
    output_tokens: Mapped[int]
    attempts: Mapped[int] = mapped_column(SmallInteger)
