import { Check, CreditCard, ExternalLink } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";

import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { cn } from "../../lib/cn";
import { trimAmount } from "../../lib/money";
import { goToPaymentPage } from "../../lib/navigation";
import { useCurrentOrganization } from "../organizations/current-organization";
import { useBilling, useOpenPortal, useStartCheckout, type Billing, type Plan } from "./api";

const POLL_FOR_MS = 60_000; // after a payment, check for the plan change for up to a minute

// Renewal dates are shown in UTC, the same calendar the server and Stripe use.
const DATE = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

const STATUS: Record<
  NonNullable<Billing["status"]>,
  { label: string; tone: "positive" | "warning" | "neutral" | "negative" }
> = {
  active: { label: "Active", tone: "positive" },
  trialing: { label: "Trial", tone: "positive" },
  past_due: { label: "Payment failed", tone: "warning" },
  incomplete: { label: "Awaiting payment", tone: "neutral" },
  incomplete_expired: { label: "Payment not completed", tone: "neutral" },
  unpaid: { label: "Unpaid", tone: "negative" },
  canceled: { label: "Cancelled", tone: "neutral" },
  paused: { label: "Paused", tone: "neutral" },
};

const PAID_ACCESS = new Set(["active", "trialing", "past_due"]);

function price(plan: Plan): string {
  return `$${trimAmount(plan.monthly_price_usd)}`;
}

export function BillingPage() {
  const organization = useCurrentOrganization();
  const isOwner = organization.my_role === "owner";
  const [searchParams] = useSearchParams();
  const checkoutResult = searchParams.get("checkout");
  const [pollUntil] = useState(() => (checkoutResult === "success" ? Date.now() + POLL_FOR_MS : 0));
  const [now, setNow] = useState(() => Date.now());

  const waitingForPayment = checkoutResult === "success" && now < pollUntil;
  const billing = useBilling(organization.id, { poll: waitingForPayment });
  const checkout = useStartCheckout(organization.id);
  const portal = useOpenPortal(organization.id);
  const [error, setError] = useState<string | null>(null);

  const data = billing.data;
  const hasPaidPlan = data?.status ? PAID_ACCESS.has(data.status) : false;
  const paymentArrived = checkoutResult === "success" && hasPaidPlan;

  useEffect(() => {
    // Stop polling once the plan has changed, or when the time runs out.
    if (!waitingForPayment || paymentArrived) return;
    const timer = window.setTimeout(() => setNow(Date.now()), 3000);
    return () => window.clearTimeout(timer);
  }, [waitingForPayment, paymentArrived, now]);

  async function redirect(getUrl: () => Promise<string>) {
    setError(null);
    try {
      goToPaymentPage(await getUrl());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Something went wrong. Try again.");
    }
  }

  const busy = checkout.isPending || portal.isPending;

  return (
    <>
      <title>{`Billing · ${organization.name} · Quantova Finance`}</title>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your plan for {organization.name}. Payments are handled securely by Stripe; card details
            never reach Quantova.
          </p>
        </div>
        {isOwner && data?.billing_enabled && data.status !== null && (
          <Button
            variant="secondary"
            loading={portal.isPending}
            disabled={busy}
            onClick={() => void redirect(() => portal.mutateAsync())}
          >
            <ExternalLink className="size-4" aria-hidden="true" />
            Manage billing
          </Button>
        )}
      </div>

      {checkoutResult === "success" && (
        <Alert
          tone={paymentArrived ? "success" : "info"}
          className="mt-6"
          title={paymentArrived ? "Your plan is active. Thank you!" : "Payment received"}
        >
          {paymentArrived
            ? "The new limits apply straight away."
            : waitingForPayment
              ? "Confirming with Stripe… your plan updates within a few seconds."
              : "Your plan will update shortly. Refresh this page in a minute."}
        </Alert>
      )}
      {checkoutResult === "cancelled" && (
        <Alert tone="info" className="mt-6" title="Checkout cancelled">
          No payment was taken.
        </Alert>
      )}
      {data && !data.billing_enabled && (
        <Alert tone="warning" className="mt-6" title="Upgrades are not available on this server">
          An administrator needs to configure a payment provider. Your current plan is unaffected.
        </Alert>
      )}
      {!isOwner && (
        <Alert tone="info" className="mt-6" title="Only owners can change billing">
          Ask an owner of {organization.name} to upgrade or manage the plan.
        </Alert>
      )}
      {error && <Alert tone="error" className="mt-6" title={error} />}

      {billing.isPending ? (
        <div className="flex justify-center py-16">
          <Spinner label="Loading billing" />
        </div>
      ) : billing.isError ? (
        <Alert tone="error" className="mt-6" title={billing.error.message} />
      ) : (
        <>
          <CurrentPlan billing={billing.data} />
          <section aria-label="Plans" className="mt-6 grid gap-4 lg:grid-cols-3">
            {billing.data.plans.map((plan) => {
              const current = plan.id === billing.data.plan.id;
              return (
                <Card key={plan.id} className={cn("flex flex-col", current && "border-brand")}>
                  <CardHeader>
                    <div className="flex items-center justify-between gap-2">
                      <CardTitle>{plan.name}</CardTitle>
                      {current && <Badge tone="brand">Current plan</Badge>}
                    </div>
                    <p className="text-sm text-muted-foreground">{plan.description}</p>
                  </CardHeader>
                  <CardContent className="flex flex-1 flex-col gap-4">
                    <p>
                      <span className="text-3xl font-semibold tracking-tight">{price(plan)}</span>
                      <span className="text-sm text-muted-foreground"> / month</span>
                    </p>
                    <ul className="grid gap-2 text-sm">
                      <li className="flex gap-2">
                        <Check className="size-4 text-positive" aria-hidden="true" />
                        {plan.max_members === 1 ? "1 member" : `Up to ${plan.max_members} members`}
                      </li>
                      <li className="flex gap-2">
                        <Check className="size-4 text-positive" aria-hidden="true" />
                        {plan.ai_insights_per_day} AI insights a day
                      </li>
                      <li className="flex gap-2">
                        <Check className="size-4 text-positive" aria-hidden="true" />
                        Transactions, reports and exports
                      </li>
                    </ul>
                    <div className="mt-auto">
                      {isOwner &&
                        billing.data.billing_enabled &&
                        !current &&
                        plan.id !== "free" &&
                        (hasPaidPlan ? (
                          <Button
                            variant="secondary"
                            className="w-full"
                            disabled={busy}
                            onClick={() => void redirect(() => portal.mutateAsync())}
                          >
                            Switch in Manage billing
                          </Button>
                        ) : (
                          <Button
                            className="w-full"
                            loading={checkout.isPending && checkout.variables === plan.id}
                            disabled={busy}
                            onClick={() => void redirect(() => checkout.mutateAsync(plan.id))}
                          >
                            <CreditCard className="size-4" aria-hidden="true" />
                            Upgrade to {plan.name}
                          </Button>
                        ))}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </section>
          <p className="mt-6 text-xs text-muted-foreground">
            Prices in US dollars, billed monthly per organization. You can cancel at any time in
            Manage billing; the plan stays active until the end of the paid period.
          </p>
        </>
      )}
    </>
  );
}

function Meter({ label, used, limit }: { label: string; used: number; limit: number }) {
  const share = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  return (
    <div className="grid gap-1.5">
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="font-mono tabular-nums">
          {used} of {limit}
        </span>
      </div>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={limit}
        aria-valuenow={used}
        className="h-2 rounded-full bg-surface-muted"
      >
        <div
          className={cn("h-full rounded-full", used >= limit ? "bg-warning" : "bg-brand")}
          style={{ width: `${share}%` }}
        />
      </div>
    </div>
  );
}

function CurrentPlan({ billing }: { billing: Billing }) {
  const status = billing.status ? STATUS[billing.status] : null;
  const periodEnd = billing.current_period_end
    ? DATE.format(new Date(billing.current_period_end))
    : null;

  return (
    <Card className="mt-6">
      <CardContent className="grid gap-6 md:grid-cols-2">
        <div className="grid content-start gap-2">
          <p className="text-sm text-muted-foreground">Current plan</p>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-2xl font-semibold tracking-tight">{billing.plan.name}</p>
            {status && <Badge tone={status.tone}>{status.label}</Badge>}
          </div>
          {billing.status === "past_due" && (
            <p className="text-sm text-muted-foreground">
              Your last payment failed. Stripe will retry it; update your card in Manage billing to
              keep your plan.
            </p>
          )}
          {periodEnd && PAID_ACCESS.has(billing.status ?? "") && (
            <p className="text-sm text-muted-foreground">
              {billing.cancel_at_period_end ? `Cancels on ${periodEnd}` : `Renews on ${periodEnd}`}
            </p>
          )}
        </div>
        <div className="grid content-start gap-4" role="group" aria-label="Usage">
          <Meter label="Members" used={billing.usage.members} limit={billing.usage.max_members} />
          <Meter
            label="AI insights today"
            used={billing.usage.ai_insights_today}
            limit={billing.usage.ai_insights_per_day}
          />
        </div>
      </CardContent>
    </Card>
  );
}
