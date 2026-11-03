"""Unit tests for reading and validating transaction CSV files. No database required."""

import re
import uuid
from decimal import Decimal

import pytest

from app.models.enums import EntryKind
from app.services.csv_import import (
    TEMPLATE_CSV,
    AccountRef,
    CsvFormatError,
    LedgerLookup,
    read_csv,
    validate_rows,
)

MAIN = AccountRef(uuid.uuid4(), "KES")
SAVINGS = AccountRef(uuid.uuid4(), "KES")
SALES = uuid.uuid4()
RENT = uuid.uuid4()

ONE_ACCOUNT = LedgerLookup(
    accounts={"main account": MAIN},
    categories={(EntryKind.INCOME, "sales"): SALES, (EntryKind.EXPENSE, "rent & utilities"): RENT},
    default_account=MAIN,
)
TWO_ACCOUNTS = LedgerLookup(
    accounts={"main account": MAIN, "savings": SAVINGS},
    categories=ONE_ACCOUNT.categories,
)

HEADER = "date,type,amount,description,category,account,counterparty,reference\n"


def csv_bytes(*lines: str, header: str = HEADER) -> bytes:
    return (header + "\n".join(lines) + "\n").encode("utf-8")


# ── Reading the file ──────────────────────────────────


def test_the_template_is_a_valid_import() -> None:
    valid, errors = validate_rows(read_csv(TEMPLATE_CSV.encode()), ONE_ACCOUNT)

    assert errors == []
    assert [row.transaction.amount for row in valid] == [Decimal("1250.50"), Decimal("320.00")]


def test_reads_excel_style_files_with_bom_and_semicolons() -> None:
    content = "﻿Date;Type;Amount;Description\n2026-10-01;income;10.00;Fee\n".encode()

    rows = read_csv(content)

    assert rows[0].values == {
        "date": "2026-10-01",
        "type": "income",
        "amount": "10.00",
        "description": "Fee",
    }


def test_row_numbers_match_the_spreadsheet_and_blank_lines_are_skipped() -> None:
    rows = read_csv(csv_bytes("2026-10-01,income,1,A,,,,", "", "2026-10-02,income,2,B,,,,"))

    assert [row.line for row in rows] == [2, 4]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", "empty"),
        (HEADER.encode(), "no transactions"),
        (b"date,type,amount\n2026-10-01,income,1\n", "Missing required column(s): description"),
        (b"date,type,amount,description,balance\n", "Unknown column(s): balance"),
        ("date,type,amount,description\n2026-10-01,income,1,Caf\xe9\n".encode("cp1252"), "UTF-8"),
    ],
)
def test_rejects_unusable_files(content: bytes, message: str) -> None:
    with pytest.raises(CsvFormatError, match=re.escape(message)):
        read_csv(content)


def test_rejects_files_with_too_many_rows() -> None:
    lines = [f"2026-10-01,income,1,Row {n},,,," for n in range(4)]

    with pytest.raises(CsvFormatError, match="more than 3 rows"):
        read_csv(csv_bytes(*lines), max_rows=3)


# ── Validating rows ───────────────────────────────────


def test_valid_rows_resolve_names_case_insensitively() -> None:
    rows = read_csv(csv_bytes("2026-10-01,Income,1250.50,Invoice,SALES,main ACCOUNT,Acme,INV-1"))

    valid, errors = validate_rows(rows, TWO_ACCOUNTS)

    assert errors == []
    transaction = valid[0].transaction
    assert transaction.kind is EntryKind.INCOME
    assert transaction.category_id == SALES
    assert transaction.account_id == MAIN.id
    assert transaction.counterparty == "Acme"
    assert valid[0].currency == "KES"


def test_account_may_be_omitted_only_when_there_is_one() -> None:
    rows = read_csv(csv_bytes("2026-10-01,income,10,Fee,,,,"))

    one_valid, one_errors = validate_rows(rows, ONE_ACCOUNT)
    _, two_errors = validate_rows(rows, TWO_ACCOUNTS)

    assert one_errors == [] and one_valid[0].transaction.account_id == MAIN.id
    assert [(e.row, e.column) for e in two_errors] == [(2, "account")]


def test_reports_every_problem_with_its_row_and_column() -> None:
    rows = read_csv(
        csv_bytes(
            "2026-13-01,income,10,Bad date,,,,",
            "2026-10-01,transfer,10,Bad type,,,,",
            "2026-10-01,income,10.12345,Too precise,,,,",
            "2026-10-01,expense,10,Wrong category kind,Sales,,,",
            "2026-10-01,income,,,Unknown,Petty cash,,",
        )
    )

    valid, errors = validate_rows(rows, ONE_ACCOUNT)

    assert valid == []
    assert {(e.row, e.column) for e in errors} == {
        (2, "date"),
        (3, "type"),
        (4, "amount"),
        (5, "category"),
        (6, "amount"),
        (6, "description"),
        (6, "category"),
        (6, "account"),
    }


def test_a_row_with_the_wrong_number_of_values_is_reported() -> None:
    rows = read_csv(csv_bytes("2026-10-01,income,1,250.00,Fee,,,,"))

    _, errors = validate_rows(rows, ONE_ACCOUNT)

    assert errors[0].row == 2
    assert "Expected 8 values but found 9" in errors[0].message
