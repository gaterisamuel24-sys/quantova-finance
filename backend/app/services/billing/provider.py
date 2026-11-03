"""The provider-neutral interface for taking payments.

The app only ever talks to `BillingProvider`. Stripe is the first implementation;
a Paystack one can be added later without changing any caller. Card details never
reach our servers: customers pay on the provider's own hosted pages.
"""

import uuid
from dataclasses import dataclass
from typing import Protocol

from app.services.billing.plans import PlanId


class BillingUnavailableError(Exception):
    """Billing is not configured on this server (no keys or price ids)."""


class BillingProviderError(Exception):
    """The provider refused or failed. The message is safe to show to users."""


@dataclass(frozen=True)
class CheckoutRequest:
    organization_id: uuid.UUID
    plan: PlanId
    customer_id: str | None  # reuse the provider customer if the organization has one
    customer_email: str
    success_url: str
    cancel_url: str


class BillingProvider(Protocol):
    name: str

    async def create_checkout(self, request: CheckoutRequest) -> str:
        """Start a hosted checkout for a subscription. Returns the URL to send the user to."""
        ...

    async def create_portal(self, *, customer_id: str, return_url: str) -> str:
        """Open the hosted portal to change plan, cancel or update the card. Returns its URL."""
        ...
