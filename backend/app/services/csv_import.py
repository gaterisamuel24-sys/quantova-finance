"""Reading and validating transaction CSV files.

Pure functions with no database access: the file is parsed into rows, and each row
is validated against a snapshot of the organization's accounts and categories. The
same rules as the API apply, because every row goes through TransactionCreate.
"""

import csv
import io
import uuid
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.models.enums import EntryKind
from app.schemas.imports import ImportRowError
from app.schemas.ledger import TransactionCreate

MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 5000
MAX_REPORTED_ERRORS = 100

REQUIRED_COLUMNS = ("date", "type", "amount", "description")
OPTIONAL_COLUMNS = ("category", "account", "counterparty", "reference")
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

# TransactionCreate field name -> CSV column name, for reporting errors in the user's terms.
COLUMN_FOR_FIELD = {
    "occurred_on": "date",
    "kind": "type",
    "amount": "amount",
    "description": "description",
    "category_id": "category",
    "account_id": "account",
    "counterparty": "counterparty",
    "reference": "reference",
}

# Stands in for an account or category that could not be resolved, so the remaining
# fields of the row can still be validated and all of its problems reported at once.
_UNRESOLVED = uuid.UUID(int=0)

TEMPLATE_CSV = (
    ",".join(ALL_COLUMNS)
    + "\r\n"
    + "2026-10-01,income,1250.50,Consulting invoice #1042,Sales,Main account,Acme Ltd,INV-1042\r\n"
    + "2026-10-03,expense,320.00,October office rent,Rent & utilities,Main account,,\r\n"
)


class CsvFormatError(Exception):
    """The file as a whole cannot be used (wrong encoding, wrong columns, too large...)."""


@dataclass(frozen=True)
class RawRow:
    line: int
    values: dict[str, str]
    problem: str | None = None


@dataclass(frozen=True)
class AccountRef:
    id: uuid.UUID
    currency: str


@dataclass(frozen=True)
class LedgerLookup:
    """The organization's active accounts and categories, keyed by case-insensitive name."""

    accounts: dict[str, AccountRef]
    categories: dict[tuple[EntryKind, str], uuid.UUID]
    default_account: AccountRef | None = None


@dataclass(frozen=True)
class ValidRow:
    line: int
    transaction: TransactionCreate
    currency: str


@dataclass
class _RowCheck:
    line: int
    errors: list[ImportRowError] = field(default_factory=list)
    reported_columns: set[str] = field(default_factory=set)

    def add(self, column: str | None, message: str) -> None:
        self.errors.append(ImportRowError(row=self.line, column=column, message=message))
        if column is not None:
            self.reported_columns.add(column)


def _decode(content: bytes) -> str:
    try:
        # utf-8-sig also removes the byte-order mark Excel adds to "CSV UTF-8" files.
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvFormatError(
            "The file is not UTF-8 encoded. In Excel, use File > Save As and choose "
            "'CSV UTF-8 (Comma delimited)'."
        ) from exc


def read_csv(content: bytes, *, max_rows: int = MAX_IMPORT_ROWS) -> list[RawRow]:
    """Parse the file into rows keyed by lower-case column name. Raises CsvFormatError."""
    text = _decode(content)
    if not text.strip():
        raise CsvFormatError("The file is empty.")

    first_line = text.splitlines()[0]
    # Excel uses ";" instead of "," in regions where "," is the decimal separator.
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)

    try:
        header = [name.strip().lower() for name in next(reader)]
        missing = [name for name in REQUIRED_COLUMNS if name not in header]
        unknown = [name for name in header if name not in ALL_COLUMNS]
        if missing:
            raise CsvFormatError(
                f"Missing required column(s): {', '.join(missing)}. "
                f"Expected columns: {', '.join(ALL_COLUMNS)}."
            )
        if unknown:
            raise CsvFormatError(
                f"Unknown column(s): {', '.join(unknown)}. "
                f"Allowed columns: {', '.join(ALL_COLUMNS)}."
            )
        if len(set(header)) != len(header):
            raise CsvFormatError("A column name appears more than once in the header row.")

        rows: list[RawRow] = []
        for record in reader:
            if not any(cell.strip() for cell in record):
                continue  # ignore blank lines
            if len(rows) >= max_rows:
                raise CsvFormatError(
                    f"The file has more than {max_rows} rows. Split it into smaller files."
                )
            line = reader.line_num
            if len(record) != len(header):
                rows.append(
                    RawRow(
                        line,
                        {},
                        f"Expected {len(header)} values but found {len(record)}. "
                        "Check for extra or missing commas.",
                    )
                )
                continue
            rows.append(
                RawRow(
                    line, {name: value.strip() for name, value in zip(header, record, strict=True)}
                )
            )
    except csv.Error as exc:
        raise CsvFormatError(
            f"The file could not be read as CSV near line {reader.line_num}."
        ) from exc

    if not rows:
        raise CsvFormatError("The file has a header row but no transactions.")
    return rows


def _friendly(message: str) -> str:
    return message.removeprefix("Value error, ")


def _check_row(row: RawRow, lookup: LedgerLookup) -> ValidRow | list[ImportRowError]:
    check = _RowCheck(row.line)
    values = row.values

    for required_column in REQUIRED_COLUMNS:
        if not values.get(required_column):
            check.add(required_column, "Required.")

    kind: EntryKind | None = None
    kind_text = values.get("type", "").lower()
    if kind_text in {k.value for k in EntryKind}:
        kind = EntryKind(kind_text)
    elif kind_text:
        check.add("type", 'Use "income" or "expense".')

    account = lookup.default_account
    account_name = values.get("account", "")
    if account_name:
        account = lookup.accounts.get(account_name.casefold())
        if account is None:
            check.add("account", f"No active account named '{account_name}'.")
    elif account is None:
        check.add("account", "Name an account: this organization has more than one.")

    category_id: uuid.UUID | None = None
    category_name = values.get("category", "")
    if category_name and kind is not None:
        category_id = lookup.categories.get((kind, category_name.casefold()))
        if category_id is None:
            check.add("category", f"No active {kind.value} category named '{category_name}'.")

    candidate: dict[str, Any] = {
        "occurred_on": values.get("date"),
        "kind": kind_text,
        "amount": values.get("amount"),
        "description": values.get("description"),
        "account_id": account.id if account else _UNRESOLVED,
        "category_id": category_id,
        "counterparty": values.get("counterparty") or None,
        "reference": values.get("reference") or None,
    }
    try:
        transaction = TransactionCreate.model_validate(candidate)
    except ValidationError as exc:
        for error in exc.errors():
            field_name = str(error["loc"][0]) if error["loc"] else None
            error_column = COLUMN_FOR_FIELD.get(field_name) if field_name else None
            if error_column not in check.reported_columns:
                check.add(error_column, _friendly(error["msg"]))
        return check.errors

    if check.errors or account is None:
        return check.errors
    return ValidRow(row.line, transaction, account.currency)


def validate_rows(
    rows: list[RawRow], lookup: LedgerLookup
) -> tuple[list[ValidRow], list[ImportRowError]]:
    """Validate every row and collect every problem, so users can fix the file in one pass."""
    valid: list[ValidRow] = []
    errors: list[ImportRowError] = []
    for row in rows:
        if row.problem is not None:
            errors.append(ImportRowError(row=row.line, column=None, message=row.problem))
            continue
        result = _check_row(row, lookup)
        if isinstance(result, ValidRow):
            valid.append(result)
        else:
            errors.extend(result)
    return valid, errors
