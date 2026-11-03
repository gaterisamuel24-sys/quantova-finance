"""Periods, buckets and percentages: the date and number rules behind analytics."""

from datetime import date
from decimal import Decimal

import pytest

from app.services.analytics_math import (
    DateRange,
    FlowTotals,
    Granularity,
    Period,
    add_months,
    bucket_end,
    bucket_start,
    build_cash_flow,
    fiscal_quarter_start,
    fiscal_year_start,
    month_end,
    percent_change,
    previous_range,
    resolve_period,
    share_percent,
)

TODAY = date(2026, 11, 3)  # a Tuesday


def test_add_months_crosses_year_boundaries() -> None:
    assert add_months(date(2026, 11, 1), 3) == date(2027, 2, 1)
    assert add_months(date(2026, 1, 1), -1) == date(2025, 12, 1)
    assert add_months(date(2026, 1, 1), -13) == date(2024, 12, 1)


def test_month_end_handles_leap_years() -> None:
    assert month_end(date(2028, 2, 10)) == date(2028, 2, 29)
    assert month_end(date(2026, 2, 10)) == date(2026, 2, 28)
    assert month_end(date(2026, 12, 31)) == date(2026, 12, 31)


@pytest.mark.parametrize(
    ("start_month", "expected"),
    [(1, date(2026, 1, 1)), (7, date(2026, 7, 1)), (12, date(2025, 12, 1))],
)
def test_fiscal_year_start(start_month: int, expected: date) -> None:
    assert fiscal_year_start(TODAY, start_month) == expected


def test_fiscal_quarters_follow_the_fiscal_year() -> None:
    # Fiscal year from July: Jul-Sep, Oct-Dec, Jan-Mar, Apr-Jun.
    assert fiscal_quarter_start(TODAY, 7) == date(2026, 10, 1)
    assert fiscal_quarter_start(date(2026, 2, 14), 7) == date(2026, 1, 1)
    # Fiscal year from February: Nov-Jan is a quarter that spans the new year.
    assert fiscal_quarter_start(date(2027, 1, 20), 2) == date(2026, 11, 1)


@pytest.mark.parametrize(
    ("period", "fiscal_start", "expected"),
    [
        (Period.THIS_MONTH, 1, DateRange(date(2026, 11, 1), date(2026, 11, 30))),
        (Period.LAST_MONTH, 1, DateRange(date(2026, 10, 1), date(2026, 10, 31))),
        (Period.THIS_QUARTER, 1, DateRange(date(2026, 10, 1), date(2026, 12, 31))),
        (Period.LAST_QUARTER, 1, DateRange(date(2026, 7, 1), date(2026, 9, 30))),
        (Period.THIS_QUARTER, 2, DateRange(date(2026, 11, 1), date(2027, 1, 31))),
        (Period.THIS_FISCAL_YEAR, 7, DateRange(date(2026, 7, 1), date(2027, 6, 30))),
        (Period.LAST_FISCAL_YEAR, 7, DateRange(date(2025, 7, 1), date(2026, 6, 30))),
        (Period.LAST_30_DAYS, 1, DateRange(date(2026, 10, 5), date(2026, 11, 3))),
        (Period.LAST_12_MONTHS, 1, DateRange(date(2025, 12, 1), date(2026, 11, 30))),
    ],
)
def test_resolve_period(period: Period, fiscal_start: int, expected: DateRange) -> None:
    assert resolve_period(period, TODAY, fiscal_start) == expected


def test_previous_range_of_a_month_is_the_whole_previous_month() -> None:
    march = DateRange(date(2026, 3, 1), date(2026, 3, 31))
    # February is shorter than March, so "same number of days" would be wrong here.
    assert previous_range(march) == DateRange(date(2026, 2, 1), date(2026, 2, 28))


def test_previous_range_of_a_quarter_is_the_previous_quarter() -> None:
    q4 = DateRange(date(2026, 10, 1), date(2026, 12, 31))
    assert previous_range(q4) == DateRange(date(2026, 7, 1), date(2026, 9, 30))


def test_previous_range_of_arbitrary_days_has_the_same_length() -> None:
    current = DateRange(date(2026, 10, 5), date(2026, 11, 3))
    previous = previous_range(current)
    assert previous == DateRange(date(2026, 9, 5), date(2026, 10, 4))
    assert previous.days == current.days == 30


def test_weeks_start_on_monday() -> None:
    assert bucket_start(TODAY, Granularity.WEEK) == date(2026, 11, 2)
    assert bucket_start(date(2026, 11, 8), Granularity.WEEK) == date(2026, 11, 2)  # Sunday
    assert bucket_start(TODAY, Granularity.MONTH) == date(2026, 11, 1)
    assert bucket_start(TODAY, Granularity.DAY) == TODAY


def test_bucket_end() -> None:
    assert bucket_end(date(2026, 11, 2), Granularity.WEEK) == date(2026, 11, 8)
    assert bucket_end(date(2026, 2, 1), Granularity.MONTH) == date(2026, 2, 28)
    assert bucket_end(TODAY, Granularity.DAY) == TODAY


def test_cash_flow_fills_empty_buckets_and_keeps_a_running_balance() -> None:
    period = DateRange(date(2026, 1, 1), date(2026, 4, 30))
    daily = [
        (date(2026, 1, 5), FlowTotals(Decimal("100.10"), Decimal("0"))),
        (date(2026, 1, 20), FlowTotals(Decimal("0.20"), Decimal("50.00"))),
        (date(2026, 3, 2), FlowTotals(Decimal("0"), Decimal("25.30"))),
    ]

    buckets = build_cash_flow(daily, period, Granularity.MONTH, Decimal("10.00"))

    assert [b.start for b in buckets] == [
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
        date(2026, 4, 1),
    ]
    assert buckets[0].totals == FlowTotals(Decimal("100.30"), Decimal("50.00"))
    assert buckets[1].totals == FlowTotals()  # February had nothing
    assert [b.closing_balance for b in buckets] == [
        Decimal("60.30"),
        Decimal("60.30"),
        Decimal("35.00"),
        Decimal("35.00"),
    ]


def test_weekly_cash_flow_includes_the_partial_first_week() -> None:
    period = DateRange(date(2026, 11, 4), date(2026, 11, 17))  # Wednesday to Tuesday
    buckets = build_cash_flow([], period, Granularity.WEEK, Decimal(0))
    assert [b.start for b in buckets] == [date(2026, 11, 2), date(2026, 11, 9), date(2026, 11, 16)]


def test_decimal_sums_are_exact() -> None:
    totals = FlowTotals(Decimal("0.10") + Decimal("0.20"), Decimal("0.30"))
    assert totals.income == Decimal("0.30")
    assert totals.net == Decimal("0")


@pytest.mark.parametrize(
    ("current", "previous", "expected"),
    [
        ("150", "100", Decimal("50.0")),
        ("50", "100", Decimal("-50.0")),
        ("1", "3", Decimal("-66.7")),
        # A loss shrinking from -200 to -50 is an improvement, so the change is positive.
        ("-50", "-200", Decimal("75.0")),
        ("100", "0", None),
    ],
)
def test_percent_change(current: str, previous: str, expected: Decimal | None) -> None:
    assert percent_change(Decimal(current), Decimal(previous)) == expected


def test_share_percent() -> None:
    assert share_percent(Decimal("1"), Decimal("3")) == Decimal("33.3")
    assert share_percent(Decimal("2"), Decimal("3")) == Decimal("66.7")
    assert share_percent(Decimal("5"), Decimal("0")) is None
