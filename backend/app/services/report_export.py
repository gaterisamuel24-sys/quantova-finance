"""Downloadable reports: CSV for spreadsheets, PDF for sharing and printing.

Pure functions with no database access. Amounts stay Decimal from the database to
the file; no floating point is involved anywhere.

CSV files are protected against formula injection ("CSV injection"): a description
such as =HYPERLINK("http://evil.example", "Click") would otherwise run as a formula
when the file is opened in Excel or Google Sheets. Every text cell that starts with
a character a spreadsheet treats as the start of a formula is prefixed with an
apostrophe, which makes the spreadsheet show it as plain text. Amount and date
cells are written by us from validated values, so they are never prefixed.
"""

import csv
import io
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from html import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.analytics import CashFlowResponse, CategorySection, ProfitLossResponse

# A spreadsheet treats a cell starting with one of these as a formula (or, for tab and
# carriage return, may strip them and then do so).
FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")
# Excel opens UTF-8 CSV files correctly only when they start with a byte order mark.
UTF8_BOM = "﻿"
TWO_PLACES = Decimal("0.01")

TRANSACTION_COLUMNS = (
    "date",
    "type",
    "amount",
    "currency",
    "description",
    "category",
    "account",
    "counterparty",
    "reference",
)


def csv_safe(text: str | None) -> str:
    """A text cell that a spreadsheet will never run as a formula."""
    if not text:
        return ""
    return f"'{text}" if text.startswith(FORMULA_TRIGGERS) else text


def plain_amount(value: Decimal) -> str:
    """An exact amount for a CSV cell: 2 decimal places, or 4 when they are needed."""
    return str(value.quantize(TWO_PLACES)) if value == value.quantize(TWO_PLACES) else str(value)


def display_amount(value: Decimal) -> str:
    """An exact amount for people to read: thousands separators, 2 or 4 decimal places."""
    places = 2 if value == value.quantize(TWO_PLACES) else 4
    return f"{value:,.{places}f}"


def _percent(value: Decimal | None) -> str:
    return "" if value is None else f"{value}%"


def _write_csv(rows: Iterable[Sequence[str]]) -> bytes:
    buffer = io.StringIO()
    buffer.write(UTF8_BOM)
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


# ── Transactions ──────────────────────────────────────


@dataclass(frozen=True)
class ExportTransaction:
    occurred_on: date
    kind: str
    amount: Decimal
    currency: str
    description: str
    category: str | None
    account: str
    counterparty: str | None
    reference: str | None


def transactions_csv(transactions: Iterable[ExportTransaction]) -> bytes:
    """The ledger as CSV. The columns are a superset of the import template's."""
    rows: list[Sequence[str]] = [TRANSACTION_COLUMNS]
    for item in transactions:
        rows.append(
            (
                item.occurred_on.isoformat(),
                item.kind,
                plain_amount(item.amount),
                item.currency,
                csv_safe(item.description),
                csv_safe(item.category),
                csv_safe(item.account),
                csv_safe(item.counterparty),
                csv_safe(item.reference),
            )
        )
    return _write_csv(rows)


# ── Profit & loss ─────────────────────────────────────


def _section_rows(title: str, section: CategorySection) -> list[Sequence[str]]:
    rows: list[Sequence[str]] = [
        (
            title,
            csv_safe(line.name),
            plain_amount(line.amount),
            str(line.transaction_count),
            _percent(line.share_pct),
        )
        for line in section.lines
    ]
    rows.append((title, f"Total {title.lower()}", plain_amount(section.total), "", ""))
    return rows


def profit_loss_csv(report: ProfitLossResponse) -> bytes:
    rows: list[Sequence[str]] = [
        ("section", "category", f"amount ({report.currency})", "transactions", "share"),
        *_section_rows("Income", report.income),
        *_section_rows("Expenses", report.expenses),
        ("Result", "Net profit", plain_amount(report.net_profit), "", ""),
        ("Result", "Profit margin", "", "", _percent(report.margin_pct)),
    ]
    return _write_csv(rows)


def profit_loss_pdf(
    report: ProfitLossResponse, *, organization_name: str, generated_at: datetime
) -> bytes:
    """A one-document profit & loss statement, ready to print or attach to an email."""
    buffer = io.BytesIO()
    period = f"{report.period.start:%d %b %Y} to {report.period.end:%d %b %Y}"
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Profit & loss, {period}",
        author="Quantova Finance",
        creator="Quantova Finance",
    )
    styles = getSampleStyleSheet()
    small = styles["Normal"].clone("small", fontSize=8, textColor=colors.HexColor("#52514e"))

    # Table cells below are plain strings, which ReportLab draws as text. Only these
    # Paragraphs interpret markup, so the user-supplied organization name is escaped.
    story = [
        Paragraph("Profit &amp; loss statement", styles["Title"]),
        Paragraph(f"{escape(organization_name)} · {period} · {report.currency}", styles["Normal"]),
        Spacer(1, 6 * mm),
    ]

    data: list[list[str]] = [["", "Transactions", "Share", f"Amount ({report.currency})"]]
    bold_rows: list[int] = []
    for title, section in (("Income", report.income), ("Expenses", report.expenses)):
        data.append([title.upper(), "", "", ""])
        bold_rows.append(len(data) - 1)
        if not section.lines:
            data.append([f"No {title.lower()} in this period", "", "", ""])
        for line in section.lines:
            data.append(
                [
                    line.name,
                    str(line.transaction_count),
                    _percent(line.share_pct),
                    display_amount(line.amount),
                ]
            )
        data.append([f"Total {title.lower()}", "", "", display_amount(section.total)])
        bold_rows.append(len(data) - 1)
    data.append(["Net profit", "", "", display_amount(report.net_profit)])
    net_row = len(data) - 1
    data.append(["Profit margin", "", "", _percent(report.margin_pct) or "—"])

    table = Table(data, colWidths=[82 * mm, 26 * mm, 22 * mm, 44 * mm], repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#52514e")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#c3c2b7")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE", (0, net_row), (-1, net_row), 1.25, colors.black),
        ("FONTNAME", (0, net_row), (-1, net_row), "Helvetica-Bold"),
        ("FONTSIZE", (0, net_row), (-1, net_row), 11),
    ]
    for row in bold_rows:
        style.append(("FONTNAME", (0, row), (-1, row), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    story += [
        table,
        Spacer(1, 8 * mm),
        Paragraph(
            "Based on the transactions recorded in Quantova Finance for this period. "
            "This is a management report, not audited financial statements, and not "
            "financial advice.",
            small,
        ),
        Paragraph(f"Generated {generated_at:%d %b %Y %H:%M} UTC.", small),
    ]
    document.build(story)
    return buffer.getvalue()


# ── Cash flow ─────────────────────────────────────────


def cash_flow_csv(report: CashFlowResponse) -> bytes:
    currency = report.currency
    rows: list[Sequence[str]] = [
        (
            "period_start",
            "period_end",
            f"income ({currency})",
            f"expenses ({currency})",
            f"net ({currency})",
            f"closing_balance ({currency})",
        )
    ]
    rows += [
        (
            point.start.isoformat(),
            point.end.isoformat(),
            plain_amount(point.income),
            plain_amount(point.expenses),
            plain_amount(point.net),
            plain_amount(point.closing_balance),
        )
        for point in report.points
    ]
    rows.append(("opening_balance", "", "", "", "", plain_amount(report.opening_balance)))
    return _write_csv(rows)
