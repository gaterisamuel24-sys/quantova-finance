"""Importing transactions from CSV: all rows or none, in one audited database transaction."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EntryKind, Transaction
from app.repositories import ledger as ledger_repo
from app.schemas.imports import ImportReport
from app.services.audit import ClientInfo, record_audit_event
from app.services.csv_import import (
    MAX_REPORTED_ERRORS,
    AccountRef,
    LedgerLookup,
    read_csv,
    validate_rows,
)
from app.services.organizations import OrgContext


async def build_lookup(session: AsyncSession, ctx: OrgContext) -> LedgerLookup:
    """Snapshot of the organization's active accounts and categories, by name."""
    accounts = [
        account
        for account in await ledger_repo.list_accounts(session, ctx.organization.id)
        if not account.is_archived
    ]
    categories = [
        category
        for category in await ledger_repo.list_categories(session, ctx.organization.id)
        if not category.is_archived
    ]
    refs = {
        account.name.casefold(): AccountRef(account.id, account.currency) for account in accounts
    }
    return LedgerLookup(
        accounts=refs,
        categories={(c.kind, c.name.casefold()): c.id for c in categories},
        # With exactly one active account, the "account" column may be left out.
        default_account=next(iter(refs.values())) if len(refs) == 1 else None,
    )


async def import_transactions(
    session: AsyncSession,
    ctx: OrgContext,
    content: bytes,
    *,
    filename: str | None,
    dry_run: bool,
    client: ClientInfo,
) -> ImportReport:
    """Validate a CSV file and, unless it is a dry run, import every row.

    Raises CsvFormatError when the file as a whole is unusable.
    """
    rows = read_csv(content)
    valid, errors = validate_rows(rows, await build_lookup(session, ctx))

    if errors:
        return ImportReport(
            status="rejected",
            filename=filename,
            row_count=len(rows),
            imported_count=0,
            error_count=len(errors),
            errors=errors[:MAX_REPORTED_ERRORS],
        )
    if dry_run:
        return ImportReport(
            status="validated",
            filename=filename,
            row_count=len(rows),
            imported_count=0,
            error_count=0,
            errors=[],
        )

    session.add_all(
        Transaction(
            organization_id=ctx.organization.id,
            account_id=row.transaction.account_id,
            category_id=row.transaction.category_id,
            kind=row.transaction.kind,
            amount=row.transaction.amount,
            currency=row.currency,
            occurred_on=row.transaction.occurred_on,
            description=row.transaction.description,
            counterparty=row.transaction.counterparty,
            reference=row.transaction.reference,
            created_by=ctx.user.id,
        )
        for row in valid
    )

    def total(kind: EntryKind) -> str:
        return str(
            sum((r.transaction.amount for r in valid if r.transaction.kind is kind), Decimal(0))
        )

    record_audit_event(
        session,
        action="transaction.imported",
        actor_user_id=ctx.user.id,
        organization_id=ctx.organization.id,
        entity_type="transaction_import",
        details={
            "filename": filename,
            "rows": len(valid),
            "income_total": total(EntryKind.INCOME),
            "expense_total": total(EntryKind.EXPENSE),
        },
        client=client,
    )
    await session.commit()
    return ImportReport(
        status="imported",
        filename=filename,
        row_count=len(rows),
        imported_count=len(valid),
        error_count=0,
        errors=[],
    )
