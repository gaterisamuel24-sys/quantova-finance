"""Ledger queries. Every function is scoped to exactly one organization."""

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, EntryKind, FinancialAccount, Transaction

LIKE_ESCAPE = "\\"


@dataclass(frozen=True)
class TransactionFilters:
    date_from: date | None = None
    date_to: date | None = None
    kind: EntryKind | None = None
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    search: str | None = None


def escape_like(text: str) -> str:
    r"""Make %, _ and \ in user input match literally inside a LIKE pattern."""
    return (
        text.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", f"{LIKE_ESCAPE}%")
        .replace("_", f"{LIKE_ESCAPE}_")
    )


def _active_in(organization_id: uuid.UUID) -> tuple[ColumnElement[bool], ...]:
    """Conditions every transaction query starts from: this organization, not deleted."""
    return (Transaction.organization_id == organization_id, Transaction.deleted_at.is_(None))


async def list_accounts(
    session: AsyncSession, organization_id: uuid.UUID
) -> list[FinancialAccount]:
    result = await session.scalars(
        select(FinancialAccount)
        .where(FinancialAccount.organization_id == organization_id)
        .order_by(FinancialAccount.name)
    )
    return list(result.all())


async def get_account(
    session: AsyncSession, organization_id: uuid.UUID, account_id: uuid.UUID
) -> FinancialAccount | None:
    return await session.scalar(
        select(FinancialAccount).where(
            FinancialAccount.organization_id == organization_id,
            FinancialAccount.id == account_id,
        )
    )


async def list_categories(session: AsyncSession, organization_id: uuid.UUID) -> list[Category]:
    result = await session.scalars(
        select(Category)
        .where(Category.organization_id == organization_id)
        .order_by(Category.kind, Category.name)
    )
    return list(result.all())


async def get_category(
    session: AsyncSession, organization_id: uuid.UUID, category_id: uuid.UUID
) -> Category | None:
    return await session.scalar(
        select(Category).where(
            Category.organization_id == organization_id, Category.id == category_id
        )
    )


async def get_transaction(
    session: AsyncSession,
    organization_id: uuid.UUID,
    transaction_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> Transaction | None:
    statement = select(Transaction).where(
        *_active_in(organization_id), Transaction.id == transaction_id
    )
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def list_transactions(
    session: AsyncSession,
    organization_id: uuid.UUID,
    filters: TransactionFilters,
    *,
    limit: int,
    offset: int,
) -> tuple[list[Transaction], int]:
    """One page of matching transactions (newest first) and the total number of matches."""
    statement = select(Transaction).where(*_active_in(organization_id))
    if filters.date_from is not None:
        statement = statement.where(Transaction.occurred_on >= filters.date_from)
    if filters.date_to is not None:
        statement = statement.where(Transaction.occurred_on <= filters.date_to)
    if filters.kind is not None:
        statement = statement.where(Transaction.kind == filters.kind)
    if filters.account_id is not None:
        statement = statement.where(Transaction.account_id == filters.account_id)
    if filters.category_id is not None:
        statement = statement.where(Transaction.category_id == filters.category_id)
    if filters.search:
        pattern = f"%{escape_like(filters.search)}%"
        statement = statement.where(
            or_(
                Transaction.description.ilike(pattern, escape=LIKE_ESCAPE),
                Transaction.counterparty.ilike(pattern, escape=LIKE_ESCAPE),
                Transaction.reference.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )

    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    page = await session.scalars(
        statement.order_by(
            Transaction.occurred_on.desc(), Transaction.created_at.desc(), Transaction.id.desc()
        )
        .limit(limit)
        .offset(offset)
    )
    return list(page.all()), total or 0
