"""Database guarantees for the ledger: tenant safety, kind matching and exact money."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AccountType,
    Category,
    EntryKind,
    FinancialAccount,
    Organization,
    Transaction,
)

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


async def make_ledger(session: AsyncSession) -> tuple[Organization, FinancialAccount, Category]:
    """An organization with one account and one income category."""
    suffix = uuid.uuid4().hex[:8]
    organization = Organization(name=f"Org {suffix}", slug=f"org-{suffix}")
    session.add(organization)
    await session.flush()
    account = FinancialAccount(
        organization_id=organization.id,
        name="Main account",
        account_type=AccountType.BANK,
        currency="USD",
    )
    category = Category(organization_id=organization.id, name="Sales", kind=EntryKind.INCOME)
    session.add_all([account, category])
    await session.flush()
    return organization, account, category


def make_transaction(
    organization: Organization,
    account: FinancialAccount,
    category: Category | None,
    *,
    kind: EntryKind = EntryKind.INCOME,
    amount: Decimal = Decimal("100.00"),
) -> Transaction:
    return Transaction(
        organization_id=organization.id,
        account_id=account.id,
        category_id=category.id if category else None,
        kind=kind,
        amount=amount,
        currency="USD",
        occurred_on=date(2026, 11, 3),
        description="Test transaction",
    )


async def test_amounts_are_stored_exactly(db_session: AsyncSession) -> None:
    organization, account, category = await make_ledger(db_session)
    transaction = make_transaction(
        organization, account, category, amount=Decimal("1234567890.1234")
    )
    db_session.add(transaction)
    await db_session.flush()
    await db_session.refresh(transaction)

    assert transaction.amount == Decimal("1234567890.1234")
    assert isinstance(transaction.amount, Decimal)


async def test_amount_must_be_positive(db_session: AsyncSession) -> None:
    organization, account, category = await make_ledger(db_session)
    db_session.add(make_transaction(organization, account, category, amount=Decimal("-5")))

    with pytest.raises(IntegrityError, match="ck_transactions_amount_positive"):
        await db_session.flush()


async def test_transaction_cannot_use_another_organizations_account(
    db_session: AsyncSession,
) -> None:
    _org_a, account_a, _ = await make_ledger(db_session)
    org_b, _, category_b = await make_ledger(db_session)

    # Organization B tries to record a transaction against Organization A's account.
    db_session.add(make_transaction(org_b, account_a, category_b))

    with pytest.raises(IntegrityError, match="fk_transactions_organization_id_financial_accounts"):
        await db_session.flush()


async def test_category_kind_must_match_transaction_kind(db_session: AsyncSession) -> None:
    organization, account, income_category = await make_ledger(db_session)

    # An expense filed under an income category.
    db_session.add(make_transaction(organization, account, income_category, kind=EntryKind.EXPENSE))

    with pytest.raises(IntegrityError, match="fk_transactions_organization_id_categories"):
        await db_session.flush()


async def test_account_with_transactions_cannot_be_deleted(db_session: AsyncSession) -> None:
    organization, account, category = await make_ledger(db_session)
    db_session.add(make_transaction(organization, account, category))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await db_session.execute(delete(FinancialAccount).where(FinancialAccount.id == account.id))
