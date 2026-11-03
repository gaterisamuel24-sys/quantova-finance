"""Plans and what each one allows. The single source of truth for plan limits.

Prices are shown for information only: what a customer is actually charged is set
in the payment provider's dashboard, and the provider tells us (via webhooks, step
6.3) which plan an organization is on. Limits are always enforced here, on the server.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class PlanId(StrEnum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class SubscriptionStatus(StrEnum):
    """Mirrors the provider's subscription states (Stripe uses these names)."""

    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"  # a payment failed; the provider is retrying
    INCOMPLETE = "incomplete"  # the first payment has not succeeded yet
    INCOMPLETE_EXPIRED = "incomplete_expired"
    UNPAID = "unpaid"
    CANCELED = "canceled"
    PAUSED = "paused"


# Statuses in which the paid plan's limits apply. PAST_DUE keeps access while the
# provider retries the payment, so one declined card does not lock a team out.
PAID_ACCESS = frozenset(
    {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE}
)


@dataclass(frozen=True)
class Plan:
    id: PlanId
    name: str
    monthly_price_usd: Decimal
    max_members: int
    ai_insights_per_day: int
    description: str


PLANS: dict[PlanId, Plan] = {
    PlanId.FREE: Plan(
        id=PlanId.FREE,
        name="Free",
        monthly_price_usd=Decimal("0"),
        max_members=1,
        ai_insights_per_day=3,
        description="For trying Quantova on your own.",
    ),
    PlanId.PRO: Plan(
        id=PlanId.PRO,
        name="Pro",
        monthly_price_usd=Decimal("19"),
        max_members=5,
        ai_insights_per_day=20,
        description="For small teams that review their finances every week.",
    ),
    PlanId.BUSINESS: Plan(
        id=PlanId.BUSINESS,
        name="Business",
        monthly_price_usd=Decimal("49"),
        max_members=25,
        ai_insights_per_day=100,
        description="For growing businesses with several people involved.",
    ),
}


def effective_plan(plan: PlanId | None, status: SubscriptionStatus | None) -> Plan:
    """The plan whose limits apply now. Anything without paid access counts as Free."""
    if plan is None or status not in PAID_ACCESS:
        return PLANS[PlanId.FREE]
    return PLANS[plan]


def ai_insights_limit(plan: Plan, server_cap: int) -> int:
    """The plan's daily allowance, never above the server-wide safety cap."""
    return min(plan.ai_insights_per_day, server_cap)
