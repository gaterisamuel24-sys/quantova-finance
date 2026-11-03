"""Ledger endpoints: accounts, categories and transactions within one organization."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import ClientInfoDep, OrgAnalyst, OrgViewer, SessionDep
from app.models import Category, EntryKind, FinancialAccount, Transaction
from app.repositories import ledger as ledger_repo
from app.repositories.ledger import TransactionFilters
from app.schemas.ledger import (
    AccountResponse,
    CategoryResponse,
    TransactionCreate,
    TransactionPage,
    TransactionResponse,
    TransactionUpdate,
)
from app.services import transactions as transaction_service

router = APIRouter(prefix="/orgs/{org_id}", tags=["ledger"])

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")


def _field_error(location: str, field: str, message: str) -> HTTPException:
    # Same shape as FastAPI's own 422 errors, so clients can show the message next to the field.
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=[{"loc": [location, field], "msg": message, "type": "value_error"}],
    )


# ── Accounts and categories ───────────────────────────


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(ctx: OrgViewer, session: SessionDep) -> list[FinancialAccount]:
    return await ledger_repo.list_accounts(session, ctx.organization.id)


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(ctx: OrgViewer, session: SessionDep) -> list[Category]:
    return await ledger_repo.list_categories(session, ctx.organization.id)


# ── Transactions ──────────────────────────────────────


@router.get("/transactions", response_model=TransactionPage)
async def list_transactions(
    ctx: OrgViewer,
    session: SessionDep,
    date_from: date | None = None,
    date_to: date | None = None,
    kind: EntryKind | None = None,
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    q: Annotated[
        str | None,
        Query(max_length=100, description="Search description, counterparty and reference"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> TransactionPage:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise _field_error("query", "date_from", "date_from must be on or before date_to.")

    search = q.strip() if q else None
    filters = TransactionFilters(
        date_from=date_from,
        date_to=date_to,
        kind=kind,
        account_id=account_id,
        category_id=category_id,
        search=search or None,
    )
    items, total = await ledger_repo.list_transactions(
        session, ctx.organization.id, filters, limit=page_size, offset=(page - 1) * page_size
    )
    return TransactionPage(
        items=[TransactionResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
async def create_transaction(
    payload: TransactionCreate, ctx: OrgAnalyst, session: SessionDep, client: ClientInfoDep
) -> Transaction:
    try:
        return await transaction_service.create_transaction(session, ctx, payload, client=client)
    except transaction_service.LedgerValidationError as exc:
        raise _field_error("body", exc.field, exc.message) from exc


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: uuid.UUID, ctx: OrgViewer, session: SessionDep
) -> Transaction:
    transaction = await ledger_repo.get_transaction(session, ctx.organization.id, transaction_id)
    if transaction is None:
        raise _not_found()
    return transaction


@router.patch("/transactions/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    ctx: OrgAnalyst,
    session: SessionDep,
    client: ClientInfoDep,
) -> Transaction:
    try:
        return await transaction_service.update_transaction(
            session,
            ctx,
            transaction_id,
            payload.model_dump(exclude_unset=True),
            client=client,
        )
    except transaction_service.TransactionNotFoundError:
        raise _not_found() from None
    except transaction_service.LedgerValidationError as exc:
        raise _field_error("body", exc.field, exc.message) from exc


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: uuid.UUID, ctx: OrgAnalyst, session: SessionDep, client: ClientInfoDep
) -> Response:
    try:
        await transaction_service.delete_transaction(session, ctx, transaction_id, client=client)
    except transaction_service.TransactionNotFoundError:
        raise _not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
