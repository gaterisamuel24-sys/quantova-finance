"""Transaction use cases: create, update and soft delete.

Each function is one unit of work: the change and its audit entry are committed
together. Rule violations are raised as domain errors; the API layer turns them
into HTTP responses.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EntryKind, FinancialAccount, Transaction
from app.repositories import ledger as ledger_repo
from app.schemas.ledger import TransactionCreate
from app.services.audit import ClientInfo, record_audit_event
from app.services.organizations import OrgContext


class TransactionNotFoundError(Exception):
    """The transaction does not exist in this organization, or has been deleted."""


class LedgerValidationError(Exception):
    """A request refers to something that is not valid within this organization."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def _jsonable(value: object) -> object:
    """Audit details are JSON: store money, IDs, dates and enums as exact strings."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (Decimal, uuid.UUID)):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


async def _require_account(
    session: AsyncSession, ctx: OrgContext, account_id: uuid.UUID
) -> FinancialAccount:
    account = await ledger_repo.get_account(session, ctx.organization.id, account_id)
    if account is None:
        raise LedgerValidationError("account_id", "Account not found in this organization.")
    if account.is_archived:
        raise LedgerValidationError("account_id", "This account is archived. Choose an active one.")
    return account


async def _require_category(
    session: AsyncSession, ctx: OrgContext, category_id: uuid.UUID, kind: EntryKind
) -> None:
    category = await ledger_repo.get_category(session, ctx.organization.id, category_id)
    if category is None:
        raise LedgerValidationError("category_id", "Category not found in this organization.")
    if category.is_archived:
        raise LedgerValidationError("category_id", "This category is archived. Choose another.")
    if category.kind is not kind:
        raise LedgerValidationError(
            "category_id",
            f"'{category.name}' is an {category.kind.value} category; "
            f"choose an {kind.value} category.",
        )


async def create_transaction(
    session: AsyncSession, ctx: OrgContext, data: TransactionCreate, *, client: ClientInfo
) -> Transaction:
    account = await _require_account(session, ctx, data.account_id)
    if data.category_id is not None:
        await _require_category(session, ctx, data.category_id, data.kind)

    transaction = Transaction(
        organization_id=ctx.organization.id,
        account_id=account.id,
        category_id=data.category_id,
        kind=data.kind,
        amount=data.amount,
        currency=account.currency,
        occurred_on=data.occurred_on,
        description=data.description,
        counterparty=data.counterparty,
        reference=data.reference,
        created_by=ctx.user.id,
    )
    session.add(transaction)
    await session.flush()
    record_audit_event(
        session,
        action="transaction.created",
        actor_user_id=ctx.user.id,
        organization_id=ctx.organization.id,
        entity_type="transaction",
        entity_id=transaction.id,
        details={
            "kind": data.kind.value,
            "amount": str(data.amount),
            "currency": account.currency,
            "occurred_on": data.occurred_on.isoformat(),
        },
        client=client,
    )
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def update_transaction(
    session: AsyncSession,
    ctx: OrgContext,
    transaction_id: uuid.UUID,
    changes: dict[str, Any],
    *,
    client: ClientInfo,
) -> Transaction:
    transaction = await ledger_repo.get_transaction(
        session, ctx.organization.id, transaction_id, for_update=True
    )
    if transaction is None:
        raise TransactionNotFoundError

    new_kind: EntryKind = changes.get("kind", transaction.kind)
    # .get() keeps an explicit null ("remove the category") and falls back only when omitted.
    new_category_id = changes.get("category_id", transaction.category_id)

    if "account_id" in changes:
        account = await _require_account(session, ctx, changes["account_id"])
        changes = {**changes, "currency": account.currency}
    # Re-check the category whenever the category or the kind changes.
    if new_category_id is not None and ("category_id" in changes or "kind" in changes):
        await _require_category(session, ctx, new_category_id, new_kind)

    diff: dict[str, dict[str, Any]] = {}
    for field, new_value in changes.items():
        old_value = getattr(transaction, field)
        if old_value != new_value:
            setattr(transaction, field, new_value)
            diff[field] = {"old": _jsonable(old_value), "new": _jsonable(new_value)}

    if diff:
        record_audit_event(
            session,
            action="transaction.updated",
            actor_user_id=ctx.user.id,
            organization_id=ctx.organization.id,
            entity_type="transaction",
            entity_id=transaction.id,
            details={"changes": diff},
            client=client,
        )
        await session.commit()
        await session.refresh(transaction)
    return transaction


async def delete_transaction(
    session: AsyncSession, ctx: OrgContext, transaction_id: uuid.UUID, *, client: ClientInfo
) -> None:
    """Soft delete: the row stays for the audit trail but disappears from the ledger."""
    transaction = await ledger_repo.get_transaction(
        session, ctx.organization.id, transaction_id, for_update=True
    )
    if transaction is None:
        raise TransactionNotFoundError

    transaction.deleted_at = datetime.now(UTC)
    record_audit_event(
        session,
        action="transaction.deleted",
        actor_user_id=ctx.user.id,
        organization_id=ctx.organization.id,
        entity_type="transaction",
        entity_id=transaction.id,
        details={
            "kind": transaction.kind.value,
            "amount": str(transaction.amount),
            "occurred_on": transaction.occurred_on.isoformat(),
            "description": transaction.description,
        },
        client=client,
    )
    await session.commit()
