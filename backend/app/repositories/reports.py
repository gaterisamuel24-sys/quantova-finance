"""Queries for report exports. Every function is scoped to one organization."""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, EntryKind, FinancialAccount, Transaction
from app.services.report_export import ExportTransaction


async def count_transactions(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    date_from: date,
    date_to: date,
    kind: EntryKind | None,
) -> int:
    query = select(func.count(Transaction.id)).where(
        Transaction.organization_id == organization_id,
        Transaction.deleted_at.is_(None),
        Transaction.occurred_on.between(date_from, date_to),
    )
    if kind is not None:
        query = query.where(Transaction.kind == kind)
    return int(await session.scalar(query) or 0)


async def export_transactions(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    date_from: date,
    date_to: date,
    kind: EntryKind | None,
) -> list[ExportTransaction]:
    """Live transactions in a date range, oldest first, with account and category names."""
    query = (
        select(Transaction, FinancialAccount.name, Category.name)
        .join(
            FinancialAccount,
            (FinancialAccount.id == Transaction.account_id)
            & (FinancialAccount.organization_id == Transaction.organization_id),
        )
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(
            Transaction.organization_id == organization_id,
            Transaction.deleted_at.is_(None),
            Transaction.occurred_on.between(date_from, date_to),
        )
        .order_by(Transaction.occurred_on, Transaction.created_at, Transaction.id)
    )
    if kind is not None:
        query = query.where(Transaction.kind == kind)

    result = await session.execute(query)
    return [
        ExportTransaction(
            occurred_on=transaction.occurred_on,
            kind=transaction.kind.value,
            amount=transaction.amount,
            currency=transaction.currency,
            description=transaction.description,
            category=category_name,
            account=account_name,
            counterparty=transaction.counterparty,
            reference=transaction.reference,
        )
        for transaction, account_name, category_name in result.all()
    ]
