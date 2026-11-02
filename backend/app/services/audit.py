"""Recording audit events."""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


@dataclass(frozen=True)
class ClientInfo:
    """Who is calling: captured from the HTTP request, stored with audit events and sessions."""

    ip_address: str | None
    user_agent: str | None


def record_audit_event(
    session: AsyncSession,
    *,
    action: str,
    client: ClientInfo | None = None,
    actor_user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Add an audit entry to the current transaction.

    It is committed together with the change it describes, so the audit trail can
    never claim something happened that was rolled back, or miss something that wasn't.
    """
    session.add(
        AuditLog(
            action=action,
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            ip_address=client.ip_address if client else None,
            user_agent=client.user_agent if client else None,
        )
    )
