"""Per-user rate limits for expensive or sensitive actions.

Plan limits (step 6.x) cap what an organization may use in a day; these cap how fast
one signed-in user can act, which stops runaway scripts, brute-force probing (such as
checking which email addresses have accounts) and accidental double submissions.

Keys use the user's id, never personal data. Like the login limits, they fail open:
if Redis is down, requests are allowed rather than locking everyone out.
"""

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status

from app.api.deps import CurrentUser
from app.core.config import Settings
from app.core.rate_limit import RateLimit, RateLimiter

HOUR = 60 * 60

AI_INSIGHTS_PER_USER = RateLimit("ai-insights-user", limit=5, window_seconds=10 * 60)
CHECKOUT_PER_USER = RateLimit("billing-checkout-user", limit=10, window_seconds=HOUR)
PORTAL_PER_USER = RateLimit("billing-portal-user", limit=20, window_seconds=HOUR)
IMPORTS_PER_USER = RateLimit("imports-user", limit=30, window_seconds=HOUR)
EXPORTS_PER_USER = RateLimit("exports-user", limit=60, window_seconds=HOUR)
MEMBER_INVITES_PER_USER = RateLimit("member-invites-user", limit=30, window_seconds=HOUR)


def rate_limited(rule: RateLimit) -> Callable[[Request, CurrentUser], Awaitable[None]]:
    """A route dependency that admits at most `rule.limit` calls per user per window."""

    async def dependency(request: Request, current_user: CurrentUser) -> None:
        settings: Settings = request.app.state.settings
        limiter = RateLimiter(request.app.state.redis, enabled=settings.rate_limit_enabled)
        decision = await limiter.hit(rule, str(current_user.id))
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="You're doing that too often. Please wait a moment and try again.",
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )

    # Lets tests check which routes are protected by which rule.
    dependency.rate_limit = rule  # type: ignore[attr-defined]
    return dependency
