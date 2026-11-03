"""Analytics endpoints: summary, cash flow and profit & loss. Any member may read them.

The reporting range is either a named `period` (default: this month) or an
explicit `date_from` + `date_to`, never both. Named quarters and years follow
the organization's fiscal year. "Today" is the current UTC date.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import OrgViewer, SessionDep
from app.schemas.analytics import CashFlowResponse, ProfitLossResponse, SummaryResponse
from app.services import analytics as analytics_service
from app.services.analytics_math import (
    MAX_BUCKETS,
    MAX_RANGE_DAYS,
    DateRange,
    Granularity,
    Period,
    bucket_starts,
    resolve_period,
)

router = APIRouter(prefix="/orgs/{org_id}/analytics", tags=["analytics"])


def _query_error(field: str, message: str) -> HTTPException:
    # Same shape as FastAPI's own 422 errors, so clients can show the message next to the field.
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=[{"loc": ["query", field], "msg": message, "type": "value_error"}],
    )


@dataclass(frozen=True)
class ReportRange:
    period: DateRange
    preset: Period | None
    today: date


def report_range(
    ctx: OrgViewer,
    period: Annotated[
        Period | None, Query(description="Named period. Defaults to this_month.")
    ] = None,
    date_from: Annotated[date | None, Query(description="Custom range start (inclusive)")] = None,
    date_to: Annotated[date | None, Query(description="Custom range end (inclusive)")] = None,
) -> ReportRange:
    today = datetime.now(UTC).date()
    custom = date_from is not None or date_to is not None

    if custom and period is not None:
        raise _query_error("period", "Use either period or date_from/date_to, not both.")
    if not custom:
        preset = period or Period.THIS_MONTH
        resolved = resolve_period(preset, today, ctx.organization.fiscal_year_start_month)
        return ReportRange(resolved, preset, today)

    if date_from is None or date_to is None:
        missing = "date_from" if date_from is None else "date_to"
        raise _query_error(missing, "Provide both date_from and date_to.")
    if date_from > date_to:
        raise _query_error("date_from", "date_from must be on or before date_to.")
    custom_range = DateRange(date_from, date_to)
    if custom_range.days > MAX_RANGE_DAYS:
        raise _query_error("date_to", f"A range can span at most {MAX_RANGE_DAYS} days.")
    return ReportRange(custom_range, None, today)


RangeDep = Annotated[ReportRange, Depends(report_range)]


@router.get("/summary", response_model=SummaryResponse)
async def summary(ctx: OrgViewer, session: SessionDep, rng: RangeDep) -> SummaryResponse:
    """Income, expenses and net for the range, compared with the period before it."""
    return await analytics_service.get_summary(
        session, ctx, rng.period, preset=rng.preset, today=rng.today
    )


@router.get("/cash-flow", response_model=CashFlowResponse)
async def cash_flow(
    ctx: OrgViewer,
    session: SessionDep,
    rng: RangeDep,
    granularity: Granularity = Granularity.MONTH,
) -> CashFlowResponse:
    """Money in and out per day, week (Monday start) or month, with running cash balance."""
    bucket_count = sum(1 for _ in bucket_starts(rng.period, granularity))
    if bucket_count > MAX_BUCKETS:
        raise _query_error(
            "granularity",
            f"That would produce {bucket_count} points (maximum {MAX_BUCKETS}). "
            "Choose a shorter range or a coarser granularity.",
        )
    return await analytics_service.get_cash_flow(
        session, ctx, rng.period, granularity, preset=rng.preset
    )


@router.get("/profit-loss", response_model=ProfitLossResponse)
async def profit_loss(ctx: OrgViewer, session: SessionDep, rng: RangeDep) -> ProfitLossResponse:
    """Income and expenses by category, with net profit and margin."""
    return await analytics_service.get_profit_loss(session, ctx, rng.period, preset=rng.preset)
