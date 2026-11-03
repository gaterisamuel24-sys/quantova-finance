"""The financial snapshot: the only data an AI model ever sees about an organization.

It is built from the analytics we already compute exactly, and contains totals only:
no transaction descriptions, no customer or supplier names, no user details and no
identifiers. Each figure is a `Fact` with a stable id, so the model can cite exactly
which figures an observation is based on, and so its answer can be checked.

Category names are the one piece of user-written text included. They are passed as
data inside JSON, and the instructions tell the model never to follow text in them.
"""

import json
from datetime import date
from decimal import ROUND_DOWN, Decimal
from typing import Literal

from pydantic import BaseModel

from app.schemas.analytics import (
    CashFlowResponse,
    CategorySection,
    ProfitLossResponse,
    SummaryResponse,
)

MAX_CATEGORIES = 5
RUNWAY_MONTHS = 3  # complete months averaged for the cash runway estimate
CENT = Decimal("0.01")
TENTH = Decimal("0.1")

Unit = Literal["money", "percent", "count", "months"]


class Fact(BaseModel):
    id: str
    label: str
    value: Decimal
    unit: Unit


class FinancialSnapshot(BaseModel):
    currency: str
    period_start: date
    period_end: date
    previous_start: date
    previous_end: date
    facts: list[Fact]

    def fact(self, fact_id: str) -> Fact | None:
        return next((item for item in self.facts if item.id == fact_id), None)

    def to_model_input(self) -> str:
        """Compact JSON for the model. Values are exact decimal strings."""
        return json.dumps(
            {
                "currency": self.currency,
                "period": {
                    "start": self.period_start.isoformat(),
                    "end": self.period_end.isoformat(),
                },
                "previous_period": {
                    "start": self.previous_start.isoformat(),
                    "end": self.previous_end.isoformat(),
                },
                "facts": [
                    {"id": f.id, "label": f.label, "value": str(f.value), "unit": f.unit}
                    for f in self.facts
                ],
            },
            ensure_ascii=False,
        )


class _Facts:
    """Collects facts, skipping figures that do not exist (a percentage with no baseline)."""

    def __init__(self) -> None:
        self.items: list[Fact] = []

    def add(self, fact_id: str, label: str, value: Decimal | None, unit: Unit) -> None:
        if value is not None:
            self.items.append(Fact(id=fact_id, label=label, value=value, unit=unit))


def _categories(facts: _Facts, prefix: str, kind: str, section: CategorySection) -> None:
    for index, line in enumerate(section.lines[:MAX_CATEGORIES], start=1):
        facts.add(f"{prefix}_{index}", f"{kind} category: {line.name}", line.amount, "money")
        facts.add(
            f"{prefix}_{index}_share_pct",
            f"Share of total {kind.lower()} for category: {line.name}",
            line.share_pct,
            "percent",
        )


def runway_estimate(
    cash_flow: CashFlowResponse, cash_balance: Decimal, today: date
) -> tuple[Decimal | None, Decimal | None]:
    """(average monthly net over the last complete months, months of cash left).

    Months of cash left is only meaningful when the business is spending more than it
    earns; otherwise it is None. Both are estimates from past figures, nothing more.
    """
    complete = [point for point in cash_flow.points if point.end < today][-RUNWAY_MONTHS:]
    if len(complete) < RUNWAY_MONTHS:
        return None, None
    average = (sum((p.net for p in complete), Decimal(0)) / RUNWAY_MONTHS).quantize(CENT)
    if average >= 0:
        return average, None
    if cash_balance <= 0:
        return average, Decimal(0)
    return average, (cash_balance / -average).quantize(TENTH, ROUND_DOWN)


def build_snapshot(
    summary: SummaryResponse,
    profit_loss: ProfitLossResponse,
    cash_flow_12_months: CashFlowResponse,
    *,
    today: date,
) -> FinancialSnapshot:
    current, previous, change = summary.current, summary.previous, summary.change
    facts = _Facts()

    facts.add("income", "Income this period", current.income, "money")
    facts.add("expenses", "Expenses this period", current.expenses, "money")
    facts.add("net_profit", "Net profit this period (income minus expenses)", current.net, "money")
    facts.add(
        "transaction_count",
        "Number of transactions this period",
        Decimal(current.transaction_count),
        "count",
    )
    facts.add("previous_income", "Income in the previous period", previous.income, "money")
    facts.add("previous_expenses", "Expenses in the previous period", previous.expenses, "money")
    facts.add("previous_net_profit", "Net profit in the previous period", previous.net, "money")
    facts.add(
        "income_change",
        "Change in income vs previous period",
        current.income - previous.income,
        "money",
    )
    facts.add(
        "expenses_change",
        "Change in expenses vs previous period",
        current.expenses - previous.expenses,
        "money",
    )
    facts.add(
        "net_profit_change",
        "Change in net profit vs previous period",
        current.net - previous.net,
        "money",
    )
    facts.add(
        "income_change_pct", "Change in income vs previous period", change.income_pct, "percent"
    )
    facts.add(
        "expenses_change_pct",
        "Change in expenses vs previous period",
        change.expenses_pct,
        "percent",
    )
    facts.add(
        "net_profit_change_pct",
        "Change in net profit vs previous period",
        change.net_pct,
        "percent",
    )
    facts.add(
        "profit_margin_pct", "Net profit as a share of income", profit_loss.margin_pct, "percent"
    )
    facts.add(
        "cash_balance",
        f"Cash balance on {summary.cash_balance_as_of.isoformat()}",
        summary.cash_balance,
        "money",
    )

    _categories(facts, "income_category", "Income", profit_loss.income)
    _categories(facts, "expense_category", "Expense", profit_loss.expenses)

    points = cash_flow_12_months.points
    facts.add(
        "income_12_months",
        "Income over the last 12 months",
        sum((p.income for p in points), Decimal(0)),
        "money",
    )
    facts.add(
        "expenses_12_months",
        "Expenses over the last 12 months",
        sum((p.expenses for p in points), Decimal(0)),
        "money",
    )
    facts.add(
        "loss_months_12_months",
        "Months with a loss in the last 12 months",
        Decimal(sum(1 for p in points if p.net < 0)),
        "count",
    )
    average, runway = runway_estimate(cash_flow_12_months, summary.cash_balance, today)
    facts.add(
        "average_monthly_net_3_months",
        "Average monthly net over the last 3 complete months",
        average,
        "money",
    )
    facts.add(
        "cash_runway_months_estimate",
        "Estimated months of cash left at that average (an estimate, not a forecast)",
        runway,
        "months",
    )

    return FinancialSnapshot(
        currency=summary.currency,
        period_start=summary.period.start,
        period_end=summary.period.end,
        previous_start=summary.previous_period.start,
        previous_end=summary.previous_period.end,
        facts=facts.items,
    )
