"""Refresh-token queries."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken


async def get_by_hash_for_update(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    """Load a token row and lock it until the transaction ends.

    The lock makes two simultaneous requests with the same token run one after the
    other, so a token can never be rotated twice.
    """
    statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    return await session.scalar(statement)


async def revoke_family(session: AsyncSession, family_id: uuid.UUID, now: datetime) -> None:
    """Revoke every still-active token descended from the same login."""
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
