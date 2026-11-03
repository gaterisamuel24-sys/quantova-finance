"""Generate, store and read AI insights for one organization.

Order of work for a new insight:
1. Check the organization's daily limit (counted from stored insights, in the database,
   so it holds even if Redis is down).
2. Compute the figures with the exact analytics services and build the snapshot.
3. End the read transaction, so no database connection is held open while the AI
   service is working (which can take several seconds).
4. Ask the model, check its answer (see explain.py), store it, audit it.
Failed attempts are audited too, because they still cost tokens.
"""

import uuid
from datetime import UTC, date, datetime, time

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIInsight
from app.repositories import insights as insights_repo
from app.schemas.insights import InsightResponse, to_response
from app.services import analytics as analytics_service
from app.services.ai.model import AIProviderError, InsightModel
from app.services.analytics_math import DateRange, Granularity, Period, resolve_period
from app.services.audit import ClientInfo, record_audit_event
from app.services.insights.explain import InsightOutput, explain_snapshot
from app.services.insights.snapshot import FinancialSnapshot, build_snapshot
from app.services.organizations import OrgContext

MAX_LISTED = 20


class DailyLimitReachedError(Exception):
    def __init__(self, limit: int) -> None:
        super().__init__(f"Daily limit of {limit} insights reached.")
        self.limit = limit


class NotEnoughDataError(Exception):
    """There are no transactions in the chosen period, so there is nothing to explain."""


def start_of_day_utc(now: datetime) -> datetime:
    return datetime.combine(now.astimezone(UTC).date(), time.min, tzinfo=UTC)


async def used_today(session: AsyncSession, organization_id: uuid.UUID, now: datetime) -> int:
    return await insights_repo.count_created_since(session, organization_id, start_of_day_utc(now))


def insight_response(insight: AIInsight) -> InsightResponse:
    return to_response(
        insight_id=insight.id,
        created_at=insight.created_at,
        period_preset=insight.period_preset,
        snapshot=FinancialSnapshot.model_validate(insight.snapshot),
        output=InsightOutput.model_validate(insight.output),
        model=insight.model,
    )


async def generate_insight(
    session: AsyncSession,
    ctx: OrgContext,
    model: InsightModel,
    *,
    preset: Period,
    now: datetime,
    daily_limit: int,
    client: ClientInfo,
) -> AIInsight:
    # Plain values, so nothing below depends on ORM objects after the transaction ends.
    organization_id = ctx.organization.id
    user_id = ctx.user.id
    fiscal_start_month = ctx.organization.fiscal_year_start_month
    today: date = now.astimezone(UTC).date()

    if await used_today(session, organization_id, now) >= daily_limit:
        raise DailyLimitReachedError(daily_limit)

    period: DateRange = resolve_period(preset, today, fiscal_start_month)
    summary = await analytics_service.get_summary(session, ctx, period, preset=preset, today=today)
    if summary.current.transaction_count == 0:
        raise NotEnoughDataError
    profit_loss = await analytics_service.get_profit_loss(session, ctx, period, preset=preset)
    last_12_months = resolve_period(Period.LAST_12_MONTHS, today, fiscal_start_month)
    cash_flow = await analytics_service.get_cash_flow(
        session, ctx, last_12_months, Granularity.MONTH, preset=Period.LAST_12_MONTHS
    )
    snapshot = build_snapshot(summary, profit_loss, cash_flow, today=today)

    # Nothing has been written; this only ends the read transaction before the slow call.
    # (The session does not expire loaded objects on commit, so ctx stays usable.)
    await session.commit()

    audit_period = {
        "period_start": snapshot.period_start.isoformat(),
        "period_end": snapshot.period_end.isoformat(),
        "preset": preset.value,
    }
    try:
        explained = await explain_snapshot(model, snapshot)
    except AIProviderError as exc:
        record_audit_event(
            session,
            action="insight.failed",
            actor_user_id=user_id,
            organization_id=organization_id,
            entity_type="ai_insight",
            details={**audit_period, "reason": str(exc)},
            client=client,
        )
        await session.commit()
        raise

    insight = AIInsight(
        organization_id=organization_id,
        created_by=user_id,
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        period_preset=preset.value,
        currency=snapshot.currency,
        snapshot=snapshot.model_dump(mode="json"),
        output=explained.output.model_dump(mode="json"),
        model=explained.model,
        input_tokens=explained.input_tokens,
        output_tokens=explained.output_tokens,
        attempts=explained.attempts,
    )
    session.add(insight)
    await session.flush()
    record_audit_event(
        session,
        action="insight.generated",
        actor_user_id=user_id,
        organization_id=organization_id,
        entity_type="ai_insight",
        entity_id=insight.id,
        details={
            **audit_period,
            "model": explained.model,
            "input_tokens": explained.input_tokens,
            "output_tokens": explained.output_tokens,
            "attempts": explained.attempts,
        },
        client=client,
    )
    await session.commit()
    await session.refresh(insight)
    return insight


async def list_insights(session: AsyncSession, ctx: OrgContext) -> list[AIInsight]:
    return await insights_repo.list_recent(session, ctx.organization.id, limit=MAX_LISTED)


async def get_insight(
    session: AsyncSession, ctx: OrgContext, insight_id: uuid.UUID
) -> AIInsight | None:
    return await insights_repo.get(session, ctx.organization.id, insight_id)
