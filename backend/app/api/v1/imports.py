"""CSV import of transactions, and a downloadable template."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status

from app.api.deps import ClientInfoDep, OrgAnalyst, OrgViewer, SessionDep
from app.api.limits import IMPORTS_PER_USER, rate_limited
from app.schemas.imports import ImportReport
from app.services import imports as import_service
from app.services.csv_import import MAX_IMPORT_BYTES, TEMPLATE_CSV, CsvFormatError

router = APIRouter(prefix="/orgs/{org_id}/transactions/import", tags=["ledger"])


@router.get("/template", response_class=Response)
async def download_template(ctx: OrgViewer) -> Response:
    """A ready-to-fill CSV with the expected columns and two example rows."""
    return Response(
        content=TEMPLATE_CSV,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="quantova-transactions-template.csv"'
        },
    )


@router.post(
    "",
    response_model=ImportReport,
    dependencies=[Depends(rate_limited(IMPORTS_PER_USER))],
)
async def import_transactions(
    file: UploadFile,
    ctx: OrgAnalyst,
    session: SessionDep,
    client: ClientInfoDep,
    dry_run: Annotated[
        bool, Query(description="Validate only; import nothing. Use it to preview a file.")
    ] = False,
) -> ImportReport:
    # Read at most one byte past the limit: enough to know the file is too large,
    # without ever holding an arbitrarily large upload in memory.
    content = await file.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"The file is larger than {MAX_IMPORT_BYTES // (1024 * 1024)} MB.",
        )
    try:
        return await import_service.import_transactions(
            session, ctx, content, filename=file.filename, dry_run=dry_run, client=client
        )
    except CsvFormatError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
