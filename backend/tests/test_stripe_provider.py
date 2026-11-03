"""The Stripe adapter: the requests it builds and how failures are reported.

A fake client stands in for Stripe, so these tests make no network calls.
"""

import uuid
from types import SimpleNamespace
from typing import Any, cast

import pytest
import stripe
from stripe import StripeClient

from app.core.config import Settings
from app.services.billing.plans import PlanId
from app.services.billing.provider import (
    BillingProviderError,
    BillingUnavailableError,
    CheckoutRequest,
)
from app.services.billing.stripe_provider import StripeBillingProvider, build_billing_provider
from tests.conftest import SettingsFactory

pytestmark = pytest.mark.anyio

ORG_ID = uuid.uuid4()


class FakeSessions:
    def __init__(self, url: str | None, error: Exception | None = None) -> None:
        self.url = url
        self.error = error
        self.params: dict[str, Any] = {}

    def create(self, params: dict[str, Any]) -> SimpleNamespace:
        self.params = params
        if self.error is not None:
            raise self.error
        return SimpleNamespace(url=self.url)


def fake_client(checkout: FakeSessions, portal: FakeSessions | None = None) -> StripeClient:
    v1 = SimpleNamespace(
        checkout=SimpleNamespace(sessions=checkout),
        billing_portal=SimpleNamespace(sessions=portal or FakeSessions("https://billing.example")),
    )
    return cast(StripeClient, SimpleNamespace(v1=v1))


def configured(settings_factory: SettingsFactory) -> Settings:
    return settings_factory(
        stripe_secret_key="sk_test_not_real",
        stripe_price_pro="price_pro_test",
        stripe_price_business="price_business_test",
    )


def request(customer_id: str | None = None, plan: PlanId = PlanId.PRO) -> CheckoutRequest:
    return CheckoutRequest(
        organization_id=ORG_ID,
        plan=plan,
        customer_id=customer_id,
        customer_email="owner@example.com",
        success_url="https://app.example/app/x/billing?checkout=success",
        cancel_url="https://app.example/app/x/billing?checkout=cancelled",
    )


def test_billing_is_off_without_keys_and_prices(settings_factory: SettingsFactory) -> None:
    for settings in (
        settings_factory(stripe_secret_key=None),
        settings_factory(stripe_secret_key="sk_test_x", stripe_price_pro=None),
        settings_factory(stripe_secret_key="", stripe_price_pro="p", stripe_price_business="b"),
    ):
        assert settings.billing_enabled is False
        with pytest.raises(BillingUnavailableError):
            build_billing_provider(settings)


def test_the_secret_key_is_never_shown(settings_factory: SettingsFactory) -> None:
    settings = configured(settings_factory)
    for view in (repr(settings), str(settings), str(settings.model_dump())):
        assert "sk_test_not_real" not in view


async def test_checkout_for_a_new_customer(settings_factory: SettingsFactory) -> None:
    sessions = FakeSessions("https://checkout.stripe.com/c/pay/cs_test_1")
    provider = StripeBillingProvider(configured(settings_factory), client=fake_client(sessions))

    url = await provider.create_checkout(request())

    assert url == "https://checkout.stripe.com/c/pay/cs_test_1"
    params = sessions.params
    assert params["mode"] == "subscription"
    assert params["line_items"] == [{"price": "price_pro_test", "quantity": 1}]
    assert params["client_reference_id"] == str(ORG_ID)
    # The organization id travels with the subscription, for matching webhooks.
    assert params["subscription_data"]["metadata"] == {
        "organization_id": str(ORG_ID),
        "plan": "pro",
    }
    assert params["customer_email"] == "owner@example.com"
    assert "customer" not in params


async def test_checkout_reuses_an_existing_customer(settings_factory: SettingsFactory) -> None:
    sessions = FakeSessions("https://checkout.stripe.com/c/pay/cs_test_2")
    provider = StripeBillingProvider(configured(settings_factory), client=fake_client(sessions))

    await provider.create_checkout(request(customer_id="cus_123", plan=PlanId.BUSINESS))

    assert sessions.params["customer"] == "cus_123"
    assert "customer_email" not in sessions.params
    assert sessions.params["line_items"][0]["price"] == "price_business_test"


async def test_the_free_plan_cannot_be_bought(settings_factory: SettingsFactory) -> None:
    provider = StripeBillingProvider(
        configured(settings_factory), client=fake_client(FakeSessions("x"))
    )

    with pytest.raises(BillingProviderError):
        await provider.create_checkout(request(plan=PlanId.FREE))


async def test_portal(settings_factory: SettingsFactory) -> None:
    portal = FakeSessions("https://billing.stripe.com/p/session/1")
    provider = StripeBillingProvider(
        configured(settings_factory), client=fake_client(FakeSessions("x"), portal)
    )

    url = await provider.create_portal(customer_id="cus_123", return_url="https://app.example/b")

    assert url == "https://billing.stripe.com/p/session/1"
    assert portal.params == {"customer": "cus_123", "return_url": "https://app.example/b"}


def stripe_error() -> Exception:
    """A Stripe exception carrying a fake key, without building HTTP objects."""
    error = stripe.StripeError.__new__(stripe.StripeError)
    Exception.__init__(error, "Invalid API Key provided: sk_test_not_real")
    return error


async def test_stripe_failures_become_neutral_messages(settings_factory: SettingsFactory) -> None:
    sessions = FakeSessions(None, error=stripe_error())
    provider = StripeBillingProvider(configured(settings_factory), client=fake_client(sessions))

    with pytest.raises(BillingProviderError, match="unavailable") as exc_info:
        await provider.create_checkout(request())

    assert "sk_test" not in str(exc_info.value)


async def test_a_missing_checkout_url_is_an_error(settings_factory: SettingsFactory) -> None:
    provider = StripeBillingProvider(
        configured(settings_factory), client=fake_client(FakeSessions(None))
    )

    with pytest.raises(BillingProviderError, match="could not be opened"):
        await provider.create_checkout(request())
