"""Fixed-window rate limiting backed by Redis."""

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

KEY_PREFIX = "ratelimit"


@dataclass(frozen=True)
class RateLimit:
    name: str
    limit: int
    window_seconds: int


LOGIN_PER_IP = RateLimit("login-ip", limit=20, window_seconds=60)
LOGIN_PER_EMAIL = RateLimit("login-email", limit=10, window_seconds=15 * 60)
REGISTER_PER_IP = RateLimit("register-ip", limit=10, window_seconds=60 * 60)
REFRESH_PER_IP = RateLimit("refresh-ip", limit=60, window_seconds=60)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


def hashed_identifier(value: str) -> str:
    """Hash identifiers such as emails so Redis keys never contain personal data."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


class RateLimiter:
    def __init__(self, redis_client: Any, *, enabled: bool = True) -> None:
        # Typed as Any: redis-py's async return types are too loose for strict mypy.
        self._redis = redis_client
        self._enabled = enabled

    async def hit(self, rule: RateLimit, identifier: str) -> RateLimitDecision:
        """Count one attempt and decide whether it is allowed."""
        if not self._enabled:
            return RateLimitDecision(allowed=True)

        key = f"{KEY_PREFIX}:{rule.name}:{identifier}"
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, rule.window_seconds, nx=True)
                count, _ = await pipe.execute()
            if count <= rule.limit:
                return RateLimitDecision(allowed=True)
            ttl = await self._redis.ttl(key)
            return RateLimitDecision(allowed=False, retry_after_seconds=max(int(ttl), 1))
        except Exception:
            # Fail open: a Redis outage must not lock every user out of login.
            logger.warning("Rate limiter unavailable; allowing request", exc_info=True)
            return RateLimitDecision(allowed=True)
