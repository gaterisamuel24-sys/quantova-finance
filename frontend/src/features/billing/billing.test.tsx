import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { goToPaymentPage, isPaymentPageUrl } from "../../lib/navigation";
import {
  createFakeBackend,
  makeBilling,
  makeOrganization,
  type FakeOrganization,
} from "../../test/fake-backend";
import { renderRoute } from "../../test/render";

// Record redirects instead of leaving the test page; keep the real URL check.
vi.mock("../../lib/navigation", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/navigation")>();
  return { ...actual, goToPaymentPage: vi.fn() };
});

beforeEach(() => {
  vi.mocked(goToPaymentPage).mockClear();
});

function open(
  billing = makeBilling(),
  { role = "owner", query = "" }: { role?: FakeOrganization["my_role"]; query?: string } = {},
) {
  const organization = makeOrganization("Acme Ltd", "USD", role);
  return renderRoute(
    `/app/${organization.id}/billing${query}`,
    createFakeBackend({ signedIn: true, organizations: [organization], billing }),
  );
}

const plans = () => screen.findByRole("region", { name: "Plans" });

describe("billing page", () => {
  it("lets an owner on Free upgrade through Stripe Checkout", async () => {
    open();

    const list = await plans();
    expect(within(list).getByText("Current plan")).toBeTruthy();
    fireEvent.click(within(list).getByRole("button", { name: "Upgrade to Pro" }));

    await waitFor(() =>
      expect(goToPaymentPage).toHaveBeenCalledWith("https://checkout.stripe.com/c/pay/cs_test_pro"),
    );
  });

  it("shows usage against the plan's limits", async () => {
    open(
      makeBilling({
        usage: { members: 1, max_members: 1, ai_insights_today: 2, ai_insights_per_day: 3 },
      }),
    );

    const insights = await screen.findByRole("meter", { name: "AI insights today" });
    expect(insights.getAttribute("aria-valuenow")).toBe("2");
    expect(insights.getAttribute("aria-valuemax")).toBe("3");
  });

  it("only owners can change billing", async () => {
    open(makeBilling(), { role: "admin" });

    expect(await screen.findByText("Only owners can change billing")).toBeTruthy();
    expect(within(await plans()).queryByRole("button")).toBeNull();
  });

  it("sends paid plans to the billing portal to change or cancel", async () => {
    open(
      makeBilling({
        planId: "pro",
        status: "active",
        current_period_end: "2026-12-03T00:00:00Z",
      }),
    );

    expect(await screen.findByText("Renews on 3 December 2026")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Manage billing" }));

    await waitFor(() =>
      expect(goToPaymentPage).toHaveBeenCalledWith(
        "https://billing.stripe.com/p/session/test_portal",
      ),
    );
    expect(
      within(await plans()).getByRole("button", { name: "Switch in Manage billing" }),
    ).toBeTruthy();
  });

  it("explains a failed payment and when a plan will end", async () => {
    open(
      makeBilling({
        planId: "pro",
        status: "past_due",
        cancel_at_period_end: true,
        current_period_end: "2026-12-03T00:00:00Z",
      }),
    );

    expect(await screen.findByText("Payment failed")).toBeTruthy();
    expect(screen.getByText(/Your last payment failed/)).toBeTruthy();
    expect(screen.getByText("Cancels on 3 December 2026")).toBeTruthy();
  });

  it("says when upgrades are not available on the server", async () => {
    open(makeBilling({ billing_enabled: false }));

    expect(await screen.findByText("Upgrades are not available on this server")).toBeTruthy();
    expect(within(await plans()).queryByRole("button")).toBeNull();
  });

  it("confirms the result of a checkout", async () => {
    open(makeBilling({ planId: "pro", status: "active" }), { query: "?checkout=success" });
    expect(await screen.findByText("Your plan is active. Thank you!")).toBeTruthy();
  });

  it("says nothing was charged when checkout is cancelled", async () => {
    open(makeBilling(), { query: "?checkout=cancelled" });
    expect(await screen.findByText("No payment was taken.")).toBeTruthy();
  });
});

describe("isPaymentPageUrl", () => {
  it("allows only Stripe's hosted pages", () => {
    expect(isPaymentPageUrl("https://checkout.stripe.com/c/pay/cs_test_1")).toBe(true);
    expect(isPaymentPageUrl("https://billing.stripe.com/p/session/1")).toBe(true);
    expect(isPaymentPageUrl("https://checkout.stripe.com.evil.example/c/pay")).toBe(false);
    expect(isPaymentPageUrl("http://checkout.stripe.com/c/pay")).toBe(false);
    expect(isPaymentPageUrl("javascript:alert(1)")).toBe(false);
  });
});
