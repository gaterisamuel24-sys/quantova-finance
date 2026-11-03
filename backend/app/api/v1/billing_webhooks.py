"""Webhook receiver for the payment provider.

This endpoint has no user authentication: Stripe calls it directly. Instead every
request must carry a valid Stripe signature, made with the webhook secret that only
Stripe and this server know, and recent enough (Stripe's default 5-minute tolerance)
that a captured request cannot be replayed later. Anything else is refused with 400.
"""

import json
import logging
from typing import Any

import stripe
from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import SessionDep, SettingsDep
from app.core.config import Settings
from app.services.billing.plans import PlanId
from app.services.billing.webhooks import handle_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing/webhooks", tags=["billing"])

MAX_PAYLOAD_BYTES = 1024 * 1024  # Stripe events are a few kilobytes


def _prices(settings: Settings) -> dict[str, PlanId]:
    prices: dict[str, PlanId] = {}
    if settings.stripe_price_pro:
        prices[settings.stripe_price_pro] = PlanId.PRO
    if settings.stripe_price_business:
        prices[settings.stripe_price_business] = PlanId.BUSINESS
    return prices


@router.post("/stripe", include_in_schema=False)
async def stripe_webhook(
    request: Request, session: SessionDep, settings: SettingsDep
) -> dict[str, str]:
    if settings.stripe_webhook_secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhooks are not configured."
        )
    payload = await request.body()
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Too large.")
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature.")

    try:
        text = payload.decode("utf-8")
        stripe.Webhook.construct_event(
            text, signature, settings.stripe_webhook_secret.get_secret_value()
        )
        event: Any = json.loads(text)
    except (stripe.SignatureVerificationError, ValueError) as exc:
        # UnicodeDecodeError and JSON errors are ValueErrors too.
        logger.warning("Rejected a webhook with an invalid signature or payload")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature."
        ) from exc
    if not isinstance(event, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload.")

    outcome = await handle_event(session, event, provider="stripe", prices=_prices(settings))
    # 200 for every verified event, including ignored and duplicate ones, so Stripe stops
    # retrying. Errors (500) make Stripe retry later, which is what we want.
    return {"status": outcome}
