"""Append-only audit trail of security-relevant and financial actions.

Rows can be inserted but never updated or deleted; a database trigger enforces
this (see the initial migration). Columns referencing users or organizations
deliberately have no foreign keys, so deleting an account can never cascade
into, or block, deletion of its audit history.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_organization_id_created_at", "organization_id", "created_at"),
        Index("ix_audit_logs_actor_user_id_created_at", "actor_user_id", "created_at"),
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    action: Mapped[str] = mapped_column(String(100))
    organization_id: Mapped[uuid.UUID | None]
    actor_user_id: Mapped[uuid.UUID | None]
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID | None]
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(512))
