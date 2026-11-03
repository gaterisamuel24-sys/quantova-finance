"""What an organization may do right now, given its subscription, and how much it has used."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import AIInsight, Membership, Subscription
from app.services.billing.plans import Plan, SubscriptionStatus, ai_insights_limit, effective_plan


@dataclass(frozen=True)
class Entitlements:
    plan: Plan
    status: SubscriptionStatus | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    max_members: int
    members: int
    ai_insights_per_day: int
    ai_insights_today: int

    @property
    def ai_insights_remaining(self) -> int:
        return max(0, self.ai_insights_per_day - self.ai_insights_today)

    @property
    def can_add_member(self) -> bool:
        return self.members < self.max_members


async def get_subscription(
    session: AsyncSession, organization_id: uuid.UUID
) -> Subscription | None:
    return await session.scalar(
        select(Subscription).where(Subscription.organization_id == organization_id)
    )


async def get_entitlements(
    session: AsyncSession, organization_id: uuid.UUID, settings: Settings, *, now: datetime
) -> Entitlements:
    subscription = await get_subscription(session, organization_id)
    plan = effective_plan(
        subscription.plan if subscription else None,
        subscription.status if subscription else None,
    )
    start_of_day = datetime.combine(now.astimezone(UTC).date(), time.min, tzinfo=UTC)
    members = await session.scalar(
        select(func.count(Membership.id)).where(Membership.organization_id == organization_id)
    )
    insights_today = await session.scalar(
        select(func.count(AIInsight.id)).where(
            AIInsight.organization_id == organization_id, AIInsight.created_at >= start_of_day
        )
    )
    return Entitlements(
        plan=plan,
        status=subscription.status if subscription else None,
        current_period_end=subscription.current_period_end if subscription else None,
        cancel_at_period_end=subscription.cancel_at_period_end if subscription else False,
        max_members=plan.max_members,
        members=int(members or 0),
        ai_insights_per_day=ai_insights_limit(plan, settings.ai_daily_insights_per_org),
        ai_insights_today=int(insights_today or 0),
    )
