"""Request and response bodies for AI insights."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.services.analytics_math import Period
from app.services.insights.explain import InsightOutput, Observation, Suggestion
from app.services.insights.snapshot import FinancialSnapshot, Unit


class InsightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: Period = Period.THIS_MONTH


class FactResponse(BaseModel):
    id: str
    label: str
    value: Decimal
    unit: Unit


class InsightResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    period_start: date
    period_end: date
    period_preset: Period | None
    currency: str
    headline: str
    observations: list[Observation]
    suggestions: list[Suggestion]
    # The exact figures the explanation was based on, so the UI can show its sources.
    facts: list[FactResponse]
    model: str


class InsightList(BaseModel):
    items: list[InsightResponse]
    ai_enabled: bool
    daily_limit: int
    remaining_today: int


def to_response(
    *,
    insight_id: uuid.UUID,
    created_at: datetime,
    period_preset: str | None,
    snapshot: FinancialSnapshot,
    output: InsightOutput,
    model: str,
) -> InsightResponse:
    return InsightResponse(
        id=insight_id,
        created_at=created_at,
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        period_preset=Period(period_preset) if period_preset else None,
        currency=snapshot.currency,
        headline=output.headline,
        observations=output.observations,
        suggestions=output.suggestions,
        facts=[FactResponse(**fact.model_dump()) for fact in snapshot.facts],
        model=model,
    )
