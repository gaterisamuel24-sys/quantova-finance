"""Housekeeping jobs that keep the database small and free of data it no longer needs.

Run them with the command-line entry point (see app/cli.py), on a schedule in
production (configured in Phase 8).
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken
from app.services.audit import record_audit_event

logger = logging.getLogger(__name__)

# Expired tokens are kept for a week after expiry, so a recent session problem can still
# be investigated. After that they are useless: an expired token is refused anyway.
REFRESH_TOKEN_GRACE = timedelta(days=7)
BATCH_SIZE = 5000  # small batches keep each delete short, so logins are never blocked


async def purge_expired_refresh_tokens(session: AsyncSession, *, now: datetime) -> int:
    """Delete refresh tokens that expired more than the grace period ago. Returns the count.

    Only expired tokens are deleted. Revoked tokens that have not yet expired are kept,
    because reuse detection depends on recognising them if they are presented again.
    """
    cutoff = now - REFRESH_TOKEN_GRACE
    total = 0
    while True:
        batch = (
            select(RefreshToken.id)
            .where(RefreshToken.expires_at < cutoff)
            .order_by(RefreshToken.expires_at)
            .limit(BATCH_SIZE)
            .scalar_subquery()
        )
        result = await session.execute(delete(RefreshToken).where(RefreshToken.id.in_(batch)))
        deleted = int(getattr(result, "rowcount", 0) or 0)
        await session.commit()
        total += deleted
        if deleted < BATCH_SIZE:
            break

    remaining = await session.scalar(select(func.count(RefreshToken.id)))
    record_audit_event(
        session,
        action="maintenance.refresh_tokens_purged",
        details={"deleted": total, "expired_before": cutoff.isoformat(), "remaining": remaining},
    )
    await session.commit()
    logger.info("Purged %d expired refresh tokens", total)
    return total
