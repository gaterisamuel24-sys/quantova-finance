"""Response bodies for billing. Prices are informational; the provider charges the real amount."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.services.billing.entitlements import Entitlements
from app.services.billing.plans import PLANS, Plan, PlanId, SubscriptionStatus


class PlanResponse(BaseModel):
    id: PlanId
    name: str
    description: str
    monthly_price_usd: Decimal
    max_members: int
    ai_insights_per_day: int


class Usage(BaseModel):
    members: int
    max_members: int
    ai_insights_today: int
    ai_insights_per_day: int


class BillingResponse(BaseModel):
    plan: PlanResponse
    status: SubscriptionStatus | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    usage: Usage
    plans: list[PlanResponse]
    # False when the server has no payment provider configured: upgrading is unavailable.
    billing_enabled: bool


def plan_response(plan: Plan) -> PlanResponse:
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        monthly_price_usd=plan.monthly_price_usd,
        max_members=plan.max_members,
        ai_insights_per_day=plan.ai_insights_per_day,
    )


def billing_response(entitlements: Entitlements, *, billing_enabled: bool) -> BillingResponse:
    return BillingResponse(
        plan=plan_response(entitlements.plan),
        status=entitlements.status,
        current_period_end=entitlements.current_period_end,
        cancel_at_period_end=entitlements.cancel_at_period_end,
        usage=Usage(
            members=entitlements.members,
            max_members=entitlements.max_members,
            ai_insights_today=entitlements.ai_insights_today,
            ai_insights_per_day=entitlements.ai_insights_per_day,
        ),
        plans=[plan_response(plan) for plan in PLANS.values()],
        billing_enabled=billing_enabled,
    )
