"""Analytics use cases: summary, cash flow and profit & loss for one organization.

Read-only, so nothing here is audited or committed. Figures are in the
organization's base currency; transactions in other currencies are left out
and counted, so the UI can say so instead of silently mixing currencies.
"""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EntryKind
from app.repositories import analytics as analytics_repo
from app.repositories.analytics import CategoryTotal
from app.schemas.analytics import (
    CashFlowPoint,
    CashFlowResponse,
    CategoryLine,
    CategorySection,
    PeriodChange,
    PeriodResponse,
    PeriodTotals,
    ProfitLossResponse,
    SummaryResponse,
)
from app.services.analytics_math import (
    ZERO,
    DateRange,
    FlowTotals,
    Granularity,
    Period,
    bucket_end,
    build_cash_flow,
    percent_change,
    previous_range,
    share_percent,
)
from app.services.organizations import OrgContext

UNCATEGORIZED = "Uncategorized"


def period_response(period: DateRange, preset: Period | None = None) -> PeriodResponse:
    return PeriodResponse(start=period.start, end=period.end, days=period.days, preset=preset)


def _totals(flow: FlowTotals, count: int) -> PeriodTotals:
    return PeriodTotals(
        income=flow.income, expenses=flow.expenses, net=flow.net, transaction_count=count
    )


async def get_summary(
    session: AsyncSession,
    ctx: OrgContext,
    period: DateRange,
    *,
    preset: Period | None,
    today: date,
) -> SummaryResponse:
    org_id = ctx.organization.id
    currency = ctx.organization.base_currency
    previous = previous_range(period)

    current_flow, current_count = await analytics_repo.period_totals(
        session, org_id, currency, period
    )
    previous_flow, previous_count = await analytics_repo.period_totals(
        session, org_id, currency, previous
    )
    # Cash "now" for a period that is still running; cash at the end for a past one.
    as_of = min(period.end, today)
    cash = await analytics_repo.balance_before(session, org_id, currency, as_of + timedelta(days=1))
    excluded = await analytics_repo.other_currency_count(session, org_id, currency, period)

    return SummaryResponse(
        currency=currency,
        period=period_response(period, preset),
        previous_period=period_response(previous),
        current=_totals(current_flow, current_count),
        previous=_totals(previous_flow, previous_count),
        change=PeriodChange(
            income_pct=percent_change(current_flow.income, previous_flow.income),
            expenses_pct=percent_change(current_flow.expenses, previous_flow.expenses),
            net_pct=percent_change(current_flow.net, previous_flow.net),
        ),
        cash_balance=cash,
        cash_balance_as_of=as_of,
        other_currency_transaction_count=excluded,
    )


async def get_cash_flow(
    session: AsyncSession,
    ctx: OrgContext,
    period: DateRange,
    granularity: Granularity,
    *,
    preset: Period | None,
) -> CashFlowResponse:
    org_id = ctx.organization.id
    currency = ctx.organization.base_currency

    opening = await analytics_repo.balance_before(session, org_id, currency, period.start)
    daily = await analytics_repo.daily_totals(session, org_id, currency, period)
    buckets = build_cash_flow(daily, period, granularity, opening)

    points = [
        CashFlowPoint(
            # The first and last weeks or months may be cut short by the period.
            start=max(bucket.start, period.start),
            end=min(bucket_end(bucket.start, granularity), period.end),
            income=bucket.totals.income,
            expenses=bucket.totals.expenses,
            net=bucket.totals.net,
            closing_balance=bucket.closing_balance,
        )
        for bucket in buckets
    ]
    return CashFlowResponse(
        currency=currency,
        period=period_response(period, preset),
        granularity=granularity,
        opening_balance=opening,
        closing_balance=buckets[-1].closing_balance if buckets else opening,
        points=points,
    )


def _section(rows: list[CategoryTotal]) -> CategorySection:
    total = sum((row.amount for row in rows), ZERO)
    return CategorySection(
        total=total,
        lines=[
            CategoryLine(
                category_id=row.category_id,
                name=row.name or UNCATEGORIZED,
                amount=row.amount,
                transaction_count=row.transaction_count,
                share_pct=share_percent(row.amount, total),
            )
            for row in rows
        ],
    )


async def get_profit_loss(
    session: AsyncSession, ctx: OrgContext, period: DateRange, *, preset: Period | None
) -> ProfitLossResponse:
    currency = ctx.organization.base_currency
    rows = await analytics_repo.totals_by_category(session, ctx.organization.id, currency, period)
    income = _section([row for row in rows if row.kind is EntryKind.INCOME])
    expenses = _section([row for row in rows if row.kind is EntryKind.EXPENSE])
    net_profit = income.total - expenses.total

    return ProfitLossResponse(
        currency=currency,
        period=period_response(period, preset),
        income=income,
        expenses=expenses,
        net_profit=net_profit,
        margin_pct=share_percent(net_profit, income.total),
    )
