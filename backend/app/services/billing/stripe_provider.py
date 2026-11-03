"""`BillingProvider` backed by Stripe Checkout and the Stripe customer portal.

The Stripe SDK's blocking calls run in a worker thread, so the API stays responsive.
These calls are rare (a user clicking "Upgrade" or "Manage billing").
"""

import logging
from collections.abc import Callable
from typing import Any, cast

import anyio
import stripe
from stripe import StripeClient

from app.core.config import Settings
from app.services.billing.plans import PlanId
from app.services.billing.provider import (
    BillingProviderError,
    BillingUnavailableError,
    CheckoutRequest,
)

logger = logging.getLogger(__name__)

MAX_NETWORK_RETRIES = 2


class StripeBillingProvider:
    name = "stripe"

    def __init__(self, settings: Settings, client: StripeClient | None = None) -> None:
        if not settings.billing_enabled or settings.stripe_secret_key is None:
            raise BillingUnavailableError("Billing is not configured on this server.")
        self._prices = {
            PlanId.PRO: settings.stripe_price_pro,
            PlanId.BUSINESS: settings.stripe_price_business,
        }
        self._client = client or StripeClient(
            settings.stripe_secret_key.get_secret_value(),
            max_network_retries=MAX_NETWORK_RETRIES,
        )

    def price_for(self, plan: PlanId) -> str:
        price = self._prices.get(plan)
        if price is None:
            raise BillingProviderError(f"The {plan.value} plan cannot be bought.")
        return price

    async def create_checkout(self, request: CheckoutRequest) -> str:
        price = self.price_for(request.plan)
        # The organization id travels with the subscription, so webhooks can match it back.
        metadata = {"organization_id": str(request.organization_id), "plan": request.plan.value}

        params: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": price, "quantity": 1}],
            "success_url": request.success_url,
            "cancel_url": request.cancel_url,
            "client_reference_id": str(request.organization_id),
            "metadata": metadata,
            "subscription_data": {"metadata": metadata},
        }
        if request.customer_id:
            params["customer"] = request.customer_id
        else:
            params["customer_email"] = request.customer_email

        def call() -> str | None:
            # cast: the SDK types params as a TypedDict; the keys above follow Stripe's API.
            session = self._client.v1.checkout.sessions.create(cast(Any, params))
            return session.url

        url = await self._run(call, "checkout")
        if not url:
            raise BillingProviderError("The payment page could not be opened. Try again.")
        return url

    async def create_portal(self, *, customer_id: str, return_url: str) -> str:
        def call() -> str:
            portal = self._client.v1.billing_portal.sessions.create(
                {"customer": customer_id, "return_url": return_url}
            )
            return portal.url

        return await self._run(call, "portal")

    @staticmethod
    async def _run[T](call: Callable[[], T], action: str) -> T:
        try:
            return await anyio.to_thread.run_sync(call)
        except stripe.StripeError as exc:
            # Details (which may include ids) go to the log; users get a neutral message.
            logger.error("Stripe %s failed: %s", action, type(exc).__name__)
            raise BillingProviderError(
                "The payment service is unavailable. Try again later."
            ) from exc


def build_billing_provider(settings: Settings) -> StripeBillingProvider:
    """The configured provider. Raises BillingUnavailableError when billing is off."""
    return StripeBillingProvider(settings)
