"""Aggregate queries for analytics. Every function is scoped to one organization.

Only live (not deleted) transactions in the given currency are counted: adding
amounts in different currencies together would produce a meaningless number.
All sums happen in PostgreSQL on NUMERIC columns, so they are exact.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, EntryKind, FinancialAccount, Transaction
from app.services.analytics_math import ZERO, DateRange, FlowTotals


@dataclass(frozen=True)
class CategoryTotal:
    kind: EntryKind
    category_id: uuid.UUID | None
    name: str | None
    amount: Decimal
    transaction_count: int


def _live(organization_id: uuid.UUID, currency: str) -> tuple[ColumnElement[bool], ...]:
    return (
        Transaction.organization_id == organization_id,
        Transaction.deleted_at.is_(None),
        Transaction.currency == currency,
    )


def _in_range(period: DateRange) -> ColumnElement[bool]:
    return Transaction.occurred_on.between(period.start, period.end)


def _sum_of(kind: EntryKind) -> ColumnElement[Decimal]:
    """SUM of amounts of one kind, or 0 when there are none (SUM of nothing is NULL)."""
    return func.coalesce(func.sum(case((Transaction.kind == kind, Transaction.amount))), ZERO)


def _signed_amount() -> ColumnElement[Decimal]:
    """Income adds to cash, expenses take away from it."""
    return case(
        (Transaction.kind == EntryKind.INCOME, Transaction.amount), else_=-Transaction.amount
    )


async def period_totals(
    session: AsyncSession, organization_id: uuid.UUID, currency: str, period: DateRange
) -> tuple[FlowTotals, int]:
    row = (
        await session.execute(
            select(
                _sum_of(EntryKind.INCOME), _sum_of(EntryKind.EXPENSE), func.count(Transaction.id)
            ).where(*_live(organization_id, currency), _in_range(period))
        )
    ).one()
    income, expenses, count = row
    return FlowTotals(Decimal(income), Decimal(expenses)), int(count)


async def balance_before(
    session: AsyncSession, organization_id: uuid.UUID, currency: str, day: date
) -> Decimal:
    """Cash at the start of `day`: opening balances plus every movement before that day."""
    opening = await session.scalar(
        select(func.coalesce(func.sum(FinancialAccount.opening_balance), ZERO)).where(
            FinancialAccount.organization_id == organization_id,
            FinancialAccount.currency == currency,
        )
    )
    movements = await session.scalar(
        select(func.coalesce(func.sum(_signed_amount()), ZERO)).where(
            *_live(organization_id, currency), Transaction.occurred_on < day
        )
    )
    return Decimal(opening or ZERO) + Decimal(movements or ZERO)


async def daily_totals(
    session: AsyncSession, organization_id: uuid.UUID, currency: str, period: DateRange
) -> list[tuple[date, FlowTotals]]:
    """Income and expenses per day that has any activity. Bucketing happens in Python."""
    result = await session.execute(
        select(Transaction.occurred_on, _sum_of(EntryKind.INCOME), _sum_of(EntryKind.EXPENSE))
        .where(*_live(organization_id, currency), _in_range(period))
        .group_by(Transaction.occurred_on)
        .order_by(Transaction.occurred_on)
    )
    return [
        (day, FlowTotals(Decimal(income), Decimal(expenses)))
        for day, income, expenses in result.all()
    ]


async def other_currency_count(
    session: AsyncSession, organization_id: uuid.UUID, currency: str, period: DateRange
) -> int:
    """Transactions left out of the figures because they are in another currency."""
    count = await session.scalar(
        select(func.count(Transaction.id)).where(
            Transaction.organization_id == organization_id,
            Transaction.deleted_at.is_(None),
            Transaction.currency != currency,
            _in_range(period),
        )
    )
    return int(count or 0)


async def totals_by_category(
    session: AsyncSession, organization_id: uuid.UUID, currency: str, period: DateRange
) -> list[CategoryTotal]:
    """Totals per (kind, category), largest first. Uncategorized rows have no category."""
    amount = func.sum(Transaction.amount)
    result = await session.execute(
        select(
            Transaction.kind,
            Category.id,
            Category.name,
            amount,
            func.count(Transaction.id),
        )
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(*_live(organization_id, currency), _in_range(period))
        .group_by(Transaction.kind, Category.id, Category.name)
        .order_by(Transaction.kind, amount.desc(), Category.name)
    )
    return [
        CategoryTotal(kind, category_id, name, Decimal(total), int(count))
        for kind, category_id, name, total, count in result.all()
    ]
