"""Plan rules: which plan applies in each subscription state, and the AI allowance."""

import pytest

from app.services.billing.plans import (
    PLANS,
    PlanId,
    SubscriptionStatus,
    ai_insights_limit,
    effective_plan,
)


def test_no_subscription_means_free() -> None:
    assert effective_plan(None, None).id is PlanId.FREE


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (SubscriptionStatus.ACTIVE, PlanId.PRO),
        (SubscriptionStatus.TRIALING, PlanId.PRO),
        (SubscriptionStatus.PAST_DUE, PlanId.PRO),  # keep access while the payment is retried
        (SubscriptionStatus.INCOMPLETE, PlanId.FREE),  # never paid
        (SubscriptionStatus.INCOMPLETE_EXPIRED, PlanId.FREE),
        (SubscriptionStatus.UNPAID, PlanId.FREE),
        (SubscriptionStatus.CANCELED, PlanId.FREE),
        (SubscriptionStatus.PAUSED, PlanId.FREE),
    ],
)
def test_paid_limits_apply_only_with_paid_access(
    status: SubscriptionStatus, expected: PlanId
) -> None:
    assert effective_plan(PlanId.PRO, status).id is expected


def test_plans_grow_in_every_limit() -> None:
    free, pro, business = PLANS[PlanId.FREE], PLANS[PlanId.PRO], PLANS[PlanId.BUSINESS]
    assert free.max_members < pro.max_members < business.max_members
    assert free.ai_insights_per_day < pro.ai_insights_per_day < business.ai_insights_per_day
    assert free.monthly_price_usd == 0


def test_server_cap_limits_every_plan() -> None:
    business = PLANS[PlanId.BUSINESS]
    assert ai_insights_limit(business, server_cap=1000) == 100
    assert ai_insights_limit(business, server_cap=10) == 10
