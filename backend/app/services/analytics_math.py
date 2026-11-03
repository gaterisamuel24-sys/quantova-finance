"""Periods, date buckets and percentages for analytics.

Pure functions with no database access. Money stays Decimal throughout; the only
rounding is of percentages, which are presentation values, to one decimal place.
"""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

ZERO = Decimal(0)
ONE_DECIMAL = Decimal("0.1")
MAX_RANGE_DAYS = 3660  # about ten years
MAX_BUCKETS = 400


class Granularity(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class Period(StrEnum):
    """Named periods. Quarters and years follow the organization's fiscal year."""

    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_QUARTER = "this_quarter"
    LAST_QUARTER = "last_quarter"
    THIS_FISCAL_YEAR = "this_fiscal_year"
    LAST_FISCAL_YEAR = "last_fiscal_year"
    LAST_30_DAYS = "last_30_days"
    LAST_12_MONTHS = "last_12_months"


@dataclass(frozen=True)
class DateRange:
    """An inclusive range of calendar days."""

    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


@dataclass(frozen=True)
class FlowTotals:
    income: Decimal = ZERO
    expenses: Decimal = ZERO

    @property
    def net(self) -> Decimal:
        return self.income - self.expenses


@dataclass(frozen=True)
class CashFlowBucket:
    start: date
    totals: FlowTotals
    closing_balance: Decimal


# ── Calendar helpers ──────────────────────────────────


def add_months(first_of_month: date, months: int) -> date:
    """The first day of the month `months` away from the given first-of-month."""
    index = first_of_month.year * 12 + first_of_month.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def month_end(any_day: date) -> date:
    return add_months(any_day.replace(day=1), 1) - timedelta(days=1)


def fiscal_year_start(today: date, start_month: int) -> date:
    year = today.year if today.month >= start_month else today.year - 1
    return date(year, start_month, 1)


def fiscal_quarter_start(today: date, start_month: int) -> date:
    year_start = fiscal_year_start(today, start_month)
    months_in = (today.year * 12 + today.month) - (year_start.year * 12 + year_start.month)
    return add_months(year_start, (months_in // 3) * 3)


# ── Periods ───────────────────────────────────────────


def resolve_period(period: Period, today: date, fiscal_start_month: int) -> DateRange:
    """Turn a named period into concrete dates, relative to `today`."""
    month_start = today.replace(day=1)
    match period:
        case Period.THIS_MONTH:
            return DateRange(month_start, month_end(month_start))
        case Period.LAST_MONTH:
            return DateRange(add_months(month_start, -1), month_start - timedelta(days=1))
        case Period.THIS_QUARTER:
            quarter = fiscal_quarter_start(today, fiscal_start_month)
            return DateRange(quarter, add_months(quarter, 3) - timedelta(days=1))
        case Period.LAST_QUARTER:
            quarter = fiscal_quarter_start(today, fiscal_start_month)
            return DateRange(add_months(quarter, -3), quarter - timedelta(days=1))
        case Period.THIS_FISCAL_YEAR:
            year = fiscal_year_start(today, fiscal_start_month)
            return DateRange(year, add_months(year, 12) - timedelta(days=1))
        case Period.LAST_FISCAL_YEAR:
            year = fiscal_year_start(today, fiscal_start_month)
            return DateRange(add_months(year, -12), year - timedelta(days=1))
        case Period.LAST_30_DAYS:
            return DateRange(today - timedelta(days=29), today)
        case Period.LAST_12_MONTHS:
            return DateRange(add_months(month_start, -11), month_end(month_start))


def previous_range(current: DateRange) -> DateRange:
    """The comparable period immediately before `current`.

    Whole calendar months compare with the same number of whole months before them
    (October with September, Q3 with Q2); any other range with the same number of days.
    """
    starts_on_first = current.start.day == 1
    if starts_on_first and current.end == month_end(current.end):
        months = (
            (current.end.year * 12 + current.end.month)
            - (current.start.year * 12 + current.start.month)
            + 1
        )
        return DateRange(add_months(current.start, -months), current.start - timedelta(days=1))
    end = current.start - timedelta(days=1)
    return DateRange(end - timedelta(days=current.days - 1), end)


# ── Buckets ───────────────────────────────────────────


def bucket_start(day: date, granularity: Granularity) -> date:
    """The first day of the bucket containing `day`. Weeks start on Monday (ISO 8601)."""
    match granularity:
        case Granularity.DAY:
            return day
        case Granularity.WEEK:
            return day - timedelta(days=day.weekday())
        case Granularity.MONTH:
            return day.replace(day=1)


def bucket_starts(period: DateRange, granularity: Granularity) -> Iterator[date]:
    current = bucket_start(period.start, granularity)
    while current <= period.end:
        yield current
        match granularity:
            case Granularity.DAY:
                current += timedelta(days=1)
            case Granularity.WEEK:
                current += timedelta(days=7)
            case Granularity.MONTH:
                current = add_months(current, 1)


def bucket_end(start: date, granularity: Granularity) -> date:
    """The last day of the bucket that begins on `start`."""
    match granularity:
        case Granularity.DAY:
            return start
        case Granularity.WEEK:
            return start + timedelta(days=6)
        case Granularity.MONTH:
            return month_end(start)


def build_cash_flow(
    daily: Iterable[tuple[date, FlowTotals]],
    period: DateRange,
    granularity: Granularity,
    opening_balance: Decimal,
) -> list[CashFlowBucket]:
    """Group daily totals into buckets, fill empty buckets with zero, add running balances."""
    sums: dict[date, FlowTotals] = {}
    for day, totals in daily:
        key = bucket_start(day, granularity)
        previous = sums.get(key, FlowTotals())
        sums[key] = FlowTotals(previous.income + totals.income, previous.expenses + totals.expenses)

    buckets: list[CashFlowBucket] = []
    balance = opening_balance
    for start in bucket_starts(period, granularity):
        totals = sums.get(start, FlowTotals())
        balance += totals.net
        buckets.append(CashFlowBucket(start, totals, balance))
    return buckets


# ── Percentages ───────────────────────────────────────


def percent_change(current: Decimal, previous: Decimal) -> Decimal | None:
    """Change from `previous` to `current` in percent, or None when there is no baseline."""
    if previous == ZERO:
        return None
    return ((current - previous) / abs(previous) * 100).quantize(ONE_DECIMAL, ROUND_HALF_UP)


def share_percent(part: Decimal, whole: Decimal) -> Decimal | None:
    """`part` as a percentage of `whole`, or None when `whole` is zero."""
    if whole == ZERO:
        return None
    return (part / whole * 100).quantize(ONE_DECIMAL, ROUND_HALF_UP)
