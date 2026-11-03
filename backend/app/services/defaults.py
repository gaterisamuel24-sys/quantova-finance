"""The starter ledger every new organization receives."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AccountType, Category, EntryKind, FinancialAccount, Organization

DEFAULT_ACCOUNT_NAME = "Main account"

DEFAULT_CATEGORIES: tuple[tuple[str, EntryKind], ...] = (
    ("Sales", EntryKind.INCOME),
    ("Services", EntryKind.INCOME),
    ("Interest income", EntryKind.INCOME),
    ("Other income", EntryKind.INCOME),
    ("Cost of goods sold", EntryKind.EXPENSE),
    ("Salaries & wages", EntryKind.EXPENSE),
    ("Rent & utilities", EntryKind.EXPENSE),
    ("Marketing", EntryKind.EXPENSE),
    ("Software & subscriptions", EntryKind.EXPENSE),
    ("Professional fees", EntryKind.EXPENSE),
    ("Travel", EntryKind.EXPENSE),
    ("Bank fees", EntryKind.EXPENSE),
    ("Taxes & licences", EntryKind.EXPENSE),
    ("Other expenses", EntryKind.EXPENSE),
)


def add_default_ledger(session: AsyncSession, organization: Organization) -> None:
    """Stage a main account and the default categories in the current transaction."""
    session.add(
        FinancialAccount(
            organization_id=organization.id,
            name=DEFAULT_ACCOUNT_NAME,
            account_type=AccountType.BANK,
            currency=organization.base_currency,
        )
    )
    session.add_all(
        Category(organization_id=organization.id, name=name, kind=kind, is_system=True)
        for name, kind in DEFAULT_CATEGORIES
    )
