"""Response bodies for analytics.

Money and percentages are Decimal, which the API sends as strings ("1250.50",
"12.5") so no precision is lost to floating point on the way to the browser.
A percentage is null when there is nothing to compare against (division by zero).
"""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.services.analytics_math import Granularity, Period


class PeriodResponse(BaseModel):
    start: date
    end: date
    days: int
    preset: Period | None = None


class PeriodTotals(BaseModel):
    income: Decimal
    expenses: Decimal
    net: Decimal
    transaction_count: int


class PeriodChange(BaseModel):
    """Percentage change from the previous period to this one."""

    income_pct: Decimal | None
    expenses_pct: Decimal | None
    net_pct: Decimal | None


class SummaryResponse(BaseModel):
    currency: str
    period: PeriodResponse
    previous_period: PeriodResponse
    current: PeriodTotals
    previous: PeriodTotals
    change: PeriodChange
    cash_balance: Decimal
    cash_balance_as_of: date
    other_currency_transaction_count: int


class CashFlowPoint(BaseModel):
    start: date
    end: date
    income: Decimal
    expenses: Decimal
    net: Decimal
    closing_balance: Decimal


class CashFlowResponse(BaseModel):
    currency: str
    period: PeriodResponse
    granularity: Granularity
    opening_balance: Decimal
    closing_balance: Decimal
    points: list[CashFlowPoint]


class CategoryLine(BaseModel):
    category_id: uuid.UUID | None
    name: str
    amount: Decimal
    transaction_count: int
    share_pct: Decimal | None


class CategorySection(BaseModel):
    total: Decimal
    lines: list[CategoryLine]


class ProfitLossResponse(BaseModel):
    currency: str
    period: PeriodResponse
    income: CategorySection
    expenses: CategorySection
    net_profit: Decimal
    margin_pct: Decimal | None
