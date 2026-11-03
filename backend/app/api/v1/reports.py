"""Report downloads: transactions, profit & loss and cash flow as CSV, and P&L as PDF.

Any member may download what they can already see in the app. Every download is
recorded in the audit log, because an export takes data outside the platform.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import ClientInfoDep, OrgViewer, SessionDep
from app.api.v1.analytics import RangeDep, ReportRange
from app.models import EntryKind
from app.repositories import reports as reports_repo
from app.services import analytics as analytics_service
from app.services import report_export
from app.services.analytics_math import MAX_BUCKETS, Granularity, bucket_starts
from app.services.audit import ClientInfo, record_audit_event
from app.services.organizations import OrgContext

router = APIRouter(prefix="/orgs/{org_id}/reports", tags=["reports"])

MAX_EXPORT_ROWS = 50_000
CSV_MEDIA_TYPE = "text/csv; charset=utf-8"
PDF_MEDIA_TYPE = "application/pdf"


def _filename(ctx: OrgContext, report: str, rng: ReportRange, extension: str) -> str:
    # The slug contains only a-z, 0-9 and hyphens, so the name is safe in a header.
    period = f"{rng.period.start.isoformat()}_{rng.period.end.isoformat()}"
    return f"{ctx.organization.slug}-{report}-{period}.{extension}"


def _download(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # Reports are private financial data: never keep a copy in a shared cache.
            "Cache-Control": "no-store",
        },
    )


async def _audit(
    session: SessionDep,
    ctx: OrgContext,
    client: ClientInfo,
    *,
    report: str,
    file_format: str,
    rng: ReportRange,
    **details: object,
) -> None:
    record_audit_event(
        session,
        action="report.exported",
        actor_user_id=ctx.user.id,
        organization_id=ctx.organization.id,
        entity_type="report",
        details={
            "report": report,
            "format": file_format,
            "date_from": rng.period.start.isoformat(),
            "date_to": rng.period.end.isoformat(),
            **details,
        },
        client=client,
    )
    await session.commit()


_CSV_RESPONSE: dict[int | str, dict[str, object]] = {
    200: {"content": {"text/csv": {}}, "description": "A CSV file"}
}


@router.get("/transactions.csv", response_class=Response, responses=_CSV_RESPONSE)
async def export_transactions(
    ctx: OrgViewer,
    session: SessionDep,
    client: ClientInfoDep,
    rng: RangeDep,
    kind: Annotated[EntryKind | None, Query(description="Only income or only expenses")] = None,
) -> Response:
    """Every transaction in the range, oldest first. Opens directly in Excel."""
    org_id = ctx.organization.id
    start, end = rng.period.start, rng.period.end
    count = await reports_repo.count_transactions(
        session, org_id, date_from=start, date_to=end, kind=kind
    )
    if count > MAX_EXPORT_ROWS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"That range has {count} transactions; a file can hold at most "
            f"{MAX_EXPORT_ROWS}. Choose a shorter range.",
        )
    rows = await reports_repo.export_transactions(
        session, org_id, date_from=start, date_to=end, kind=kind
    )
    await _audit(
        session, ctx, client, report="transactions", file_format="csv", rng=rng, rows=len(rows)
    )
    content = report_export.transactions_csv(rows)
    return _download(content, CSV_MEDIA_TYPE, _filename(ctx, "transactions", rng, "csv"))


@router.get("/profit-loss.csv", response_class=Response, responses=_CSV_RESPONSE)
async def export_profit_loss_csv(
    ctx: OrgViewer, session: SessionDep, client: ClientInfoDep, rng: RangeDep
) -> Response:
    report = await analytics_service.get_profit_loss(session, ctx, rng.period, preset=rng.preset)
    await _audit(session, ctx, client, report="profit_loss", file_format="csv", rng=rng)
    content = report_export.profit_loss_csv(report)
    return _download(content, CSV_MEDIA_TYPE, _filename(ctx, "profit-loss", rng, "csv"))


@router.get(
    "/profit-loss.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "A PDF file"}},
)
async def export_profit_loss_pdf(
    ctx: OrgViewer, session: SessionDep, client: ClientInfoDep, rng: RangeDep
) -> Response:
    report = await analytics_service.get_profit_loss(session, ctx, rng.period, preset=rng.preset)
    await _audit(session, ctx, client, report="profit_loss", file_format="pdf", rng=rng)
    content = report_export.profit_loss_pdf(
        report, organization_name=ctx.organization.name, generated_at=datetime.now(UTC)
    )
    return _download(content, PDF_MEDIA_TYPE, _filename(ctx, "profit-loss", rng, "pdf"))


@router.get("/cash-flow.csv", response_class=Response, responses=_CSV_RESPONSE)
async def export_cash_flow_csv(
    ctx: OrgViewer,
    session: SessionDep,
    client: ClientInfoDep,
    rng: RangeDep,
    granularity: Granularity = Granularity.MONTH,
) -> Response:
    bucket_count = sum(1 for _ in bucket_starts(rng.period, granularity))
    if bucket_count > MAX_BUCKETS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"That would produce {bucket_count} rows (maximum {MAX_BUCKETS}). "
            "Choose a shorter range or a coarser granularity.",
        )
    report = await analytics_service.get_cash_flow(
        session, ctx, rng.period, granularity, preset=rng.preset
    )
    await _audit(
        session,
        ctx,
        client,
        report="cash_flow",
        file_format="csv",
        rng=rng,
        granularity=granularity.value,
    )
    content = report_export.cash_flow_csv(report)
    return _download(content, CSV_MEDIA_TYPE, _filename(ctx, "cash-flow", rng, "csv"))
