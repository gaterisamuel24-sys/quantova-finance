"""AI insight endpoints. Any member can read insights; analysts and above can generate them."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import ClientInfoDep, OrgAnalyst, OrgViewer, SessionDep, SettingsDep
from app.api.limits import AI_INSIGHTS_PER_USER, rate_limited
from app.schemas.insights import InsightList, InsightRequest, InsightResponse
from app.services.ai.model import AIProviderError, AIUnavailableError, InsightModel
from app.services.ai.openai_model import build_insight_model
from app.services.billing.entitlements import get_entitlements
from app.services.insights import service as insight_service

router = APIRouter(prefix="/orgs/{org_id}/insights", tags=["insights"])


def get_insight_model(settings: SettingsDep) -> InsightModel:
    """The configured AI model. Tests replace this dependency with a fake."""
    try:
        return build_insight_model(settings)
    except AIUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI insights are not configured on this server.",
        ) from None


InsightModelDep = Annotated[InsightModel, Depends(get_insight_model)]


@router.get("", response_model=InsightList)
async def list_insights(ctx: OrgViewer, session: SessionDep, settings: SettingsDep) -> InsightList:
    """The latest insights, newest first, and how many more the plan allows today."""
    insights = await insight_service.list_insights(session, ctx)
    entitlements = await get_entitlements(
        session, ctx.organization.id, settings, now=datetime.now(UTC)
    )
    return InsightList(
        items=[insight_service.insight_response(insight) for insight in insights],
        ai_enabled=settings.ai_enabled,
        daily_limit=entitlements.ai_insights_per_day,
        remaining_today=entitlements.ai_insights_remaining,
    )


@router.post(
    "",
    response_model=InsightResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limited(AI_INSIGHTS_PER_USER))],
)
async def generate_insight(
    payload: InsightRequest,
    ctx: OrgAnalyst,
    session: SessionDep,
    settings: SettingsDep,
    client: ClientInfoDep,
    model: InsightModelDep,
) -> InsightResponse:
    """Explain the period's figures in plain language. Uses the AI service."""
    now = datetime.now(UTC)
    # The daily allowance comes from the organization's plan (capped server-wide).
    entitlements = await get_entitlements(session, ctx.organization.id, settings, now=now)
    try:
        insight = await insight_service.generate_insight(
            session,
            ctx,
            model,
            preset=payload.period,
            now=now,
            daily_limit=entitlements.ai_insights_per_day,
            client=client,
        )
    except insight_service.DailyLimitReachedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"The {entitlements.plan.name} plan includes {exc.limit} insights a day, "
            "and they have all been used. The allowance resets at midnight UTC.",
        ) from exc
    except insight_service.NotEnoughDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="There are no transactions in this period yet. Add some, then try again.",
        ) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return insight_service.insight_response(insight)


@router.get("/{insight_id}", response_model=InsightResponse)
async def get_insight(
    insight_id: uuid.UUID, ctx: OrgViewer, session: SessionDep
) -> InsightResponse:
    insight = await insight_service.get_insight(session, ctx, insight_id)
    if insight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found.")
    return insight_service.insight_response(insight)
