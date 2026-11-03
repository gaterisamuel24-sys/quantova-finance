"""AI insight queries. Every function is scoped to one organization."""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIInsight


async def count_created_since(
    session: AsyncSession, organization_id: uuid.UUID, since: datetime
) -> int:
    count = await session.scalar(
        select(func.count(AIInsight.id)).where(
            AIInsight.organization_id == organization_id, AIInsight.created_at >= since
        )
    )
    return int(count or 0)


async def list_recent(
    session: AsyncSession, organization_id: uuid.UUID, *, limit: int
) -> list[AIInsight]:
    result = await session.scalars(
        select(AIInsight)
        .where(AIInsight.organization_id == organization_id)
        .order_by(AIInsight.created_at.desc(), AIInsight.id.desc())
        .limit(limit)
    )
    return list(result.all())


async def get(
    session: AsyncSession, organization_id: uuid.UUID, insight_id: uuid.UUID
) -> AIInsight | None:
    return await session.scalar(
        select(AIInsight).where(
            AIInsight.organization_id == organization_id, AIInsight.id == insight_id
        )
    )
