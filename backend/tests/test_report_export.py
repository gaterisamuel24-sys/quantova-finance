"""CSV and PDF report files: exact amounts and protection against formula injection."""

import csv
import io
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.schemas.analytics import (
    CashFlowPoint,
    CashFlowResponse,
    CategoryLine,
    CategorySection,
    PeriodResponse,
    ProfitLossResponse,
)
from app.services.analytics_math import Granularity
from app.services.report_export import (
    UTF8_BOM,
    ExportTransaction,
    cash_flow_csv,
    csv_safe,
    display_amount,
    plain_amount,
    profit_loss_csv,
    profit_loss_pdf,
    transactions_csv,
)

OCTOBER = PeriodResponse(start=date(2026, 10, 1), end=date(2026, 10, 31), days=31)


def read_rows(content: bytes) -> list[list[str]]:
    text = content.decode("utf-8")
    assert text.startswith(UTF8_BOM)  # so Excel reads the file as UTF-8
    return list(csv.reader(io.StringIO(text.removeprefix(UTF8_BOM))))


def line(name: str, amount: str, count: int, share: str | None) -> CategoryLine:
    return CategoryLine(
        category_id=uuid.uuid4(),
        name=name,
        amount=Decimal(amount),
        transaction_count=count,
        share_pct=None if share is None else Decimal(share),
    )


def profit_loss() -> ProfitLossResponse:
    return ProfitLossResponse(
        currency="KES",
        period=OCTOBER,
        income=CategorySection(
            total=Decimal("1250.5000"), lines=[line("Sales", "1250.5000", 2, "100.0")]
        ),
        expenses=CategorySection(
            total=Decimal("300.2500"),
            lines=[line('=HYPERLINK("http://evil.example")', "300.2500", 1, "100.0")],
        ),
        net_profit=Decimal("950.2500"),
        margin_pct=Decimal("76.0"),
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("=1+1", "'=1+1"),
        ("+254 700 000000", "'+254 700 000000"),
        ("-cmd", "'-cmd"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("\t=1", "'\t=1"),
        ("Office rent", "Office rent"),
        ("Rent = 300", "Rent = 300"),
        (None, ""),
        ("", ""),
    ],
)
def test_csv_safe_neutralises_formulas(text: str | None, expected: str) -> None:
    assert csv_safe(text) == expected


@pytest.mark.parametrize(
    ("value", "plain", "display"),
    [
        ("1250.5000", "1250.50", "1,250.50"),
        ("0.1234", "0.1234", "0.1234"),
        ("-300.0000", "-300.00", "-300.00"),
        ("999999999999999.9999", "999999999999999.9999", "999,999,999,999,999.9999"),
    ],
)
def test_amounts_are_exact(value: str, plain: str, display: str) -> None:
    assert plain_amount(Decimal(value)) == plain
    assert display_amount(Decimal(value)) == display


def test_transactions_csv() -> None:
    content = transactions_csv(
        [
            ExportTransaction(
                occurred_on=date(2026, 10, 3),
                kind="expense",
                amount=Decimal("320.0000"),
                currency="KES",
                description="=cmd|' /C calc'!A0",
                category=None,
                account="Main account",
                counterparty="Landlord, Ltd",
                reference=None,
            )
        ]
    )

    header, row = read_rows(content)
    assert header[:4] == ["date", "type", "amount", "currency"]
    assert row == [
        "2026-10-03",
        "expense",
        "320.00",
        "KES",
        "'=cmd|' /C calc'!A0",
        "",
        "Main account",
        "Landlord, Ltd",  # the comma is quoted correctly, not split into two cells
        "",
    ]


def test_profit_loss_csv() -> None:
    rows = read_rows(profit_loss_csv(profit_loss()))

    assert rows[0] == ["section", "category", "amount (KES)", "transactions", "share"]
    assert ["Income", "Sales", "1250.50", "2", "100.0%"] in rows
    assert ["Expenses", '\'=HYPERLINK("http://evil.example")', "300.25", "1", "100.0%"] in rows
    assert ["Result", "Net profit", "950.25", "", ""] in rows
    assert ["Result", "Profit margin", "", "", "76.0%"] in rows


def test_cash_flow_csv() -> None:
    report = CashFlowResponse(
        currency="KES",
        period=OCTOBER,
        granularity=Granularity.MONTH,
        opening_balance=Decimal("100.0000"),
        closing_balance=Decimal("-50.0000"),
        points=[
            CashFlowPoint(
                start=date(2026, 10, 1),
                end=date(2026, 10, 31),
                income=Decimal("0.1000"),
                expenses=Decimal("150.1000"),
                net=Decimal("-150.0000"),
                closing_balance=Decimal("-50.0000"),
            )
        ],
    )

    rows = read_rows(cash_flow_csv(report))

    assert rows[1] == ["2026-10-01", "2026-10-31", "0.10", "150.10", "-150.00", "-50.00"]
    assert rows[-1] == ["opening_balance", "", "", "", "", "100.00"]


def test_profit_loss_pdf() -> None:
    content = profit_loss_pdf(
        profit_loss(),
        organization_name="Acme <b>Ltd</b> & Co",
        generated_at=datetime(2026, 11, 3, 12, 0, tzinfo=UTC),
    )

    assert content.startswith(b"%PDF-")
    assert content.rstrip().endswith(b"%%EOF")
    assert len(content) > 1000
