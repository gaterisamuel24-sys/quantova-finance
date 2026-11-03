"""A stand-in payment provider, so tests never call Stripe or need keys."""

from dataclasses import dataclass, field

from app.services.billing.provider import BillingProviderError, CheckoutRequest


@dataclass
class FakeBillingProvider:
    name: str = "fake"
    fail: bool = False
    checkouts: list[CheckoutRequest] = field(default_factory=list)
    portals: list[tuple[str, str]] = field(default_factory=list)

    async def create_checkout(self, request: CheckoutRequest) -> str:
        if self.fail:
            raise BillingProviderError("The payment service is unavailable. Try again later.")
        self.checkouts.append(request)
        return f"https://checkout.stripe.com/c/pay/cs_test_{len(self.checkouts)}"

    async def create_portal(self, *, customer_id: str, return_url: str) -> str:
        if self.fail:
            raise BillingProviderError("The payment service is unavailable. Try again later.")
        self.portals.append((customer_id, return_url))
        return "https://billing.stripe.com/p/session/test_portal"
