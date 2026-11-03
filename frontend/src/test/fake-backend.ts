import type { components } from "../lib/api/schema";
import { json, type FetchHandler } from "./fake-api";

export const PASSWORD = "correct horse battery staple";

type FakeUser = {
  id: string;
  email: string;
  full_name: string;
  is_email_verified: boolean;
  platform_role: "user";
  created_at: string;
};

type OrgRole = components["schemas"]["OrganizationResponse"]["my_role"];
type Account = components["schemas"]["AccountResponse"];
type Category = components["schemas"]["CategoryResponse"];
type Transaction = components["schemas"]["TransactionResponse"];
type ImportReport = components["schemas"]["ImportReport"];
type Summary = components["schemas"]["SummaryResponse"];
type CashFlow = components["schemas"]["CashFlowResponse"];
type ProfitLoss = components["schemas"]["ProfitLossResponse"];

type Insight = components["schemas"]["InsightResponse"];
type Billing = components["schemas"]["BillingResponse"];
type PlanResponse = components["schemas"]["PlanResponse"];

const PLANS: PlanResponse[] = [
  {
    id: "free",
    name: "Free",
    description: "For trying Quantova on your own.",
    monthly_price_usd: "0",
    max_members: 1,
    ai_insights_per_day: 3,
  },
  {
    id: "pro",
    name: "Pro",
    description: "For small teams.",
    monthly_price_usd: "19",
    max_members: 5,
    ai_insights_per_day: 20,
  },
  {
    id: "business",
    name: "Business",
    description: "For growing businesses.",
    monthly_price_usd: "49",
    max_members: 25,
    ai_insights_per_day: 100,
  },
];

/** A billing response, Free by default. */
export function makeBilling(
  fields: Partial<Billing> & { planId?: PlanResponse["id"] } = {},
): Billing {
  const { planId = "free", ...rest } = fields;
  const plan = PLANS.find((candidate) => candidate.id === planId) ?? PLANS[0];
  return {
    plan,
    status: null,
    current_period_end: null,
    cancel_at_period_end: false,
    usage: {
      members: 1,
      max_members: plan.max_members,
      ai_insights_today: 0,
      ai_insights_per_day: plan.ai_insights_per_day,
    },
    plans: PLANS,
    billing_enabled: true,
    ...rest,
  };
}

/** How the fake insights API behaves. */
export type FakeInsights = {
  aiEnabled?: boolean;
  dailyLimit?: number;
  /** Insights that already exist, newest first. */
  existing?: Insight[];
  /** Make generation fail with this HTTP status and message. */
  failWith?: { status: number; detail: string };
};

export function makeInsight(currency = "USD", fields: Partial<Insight> = {}): Insight {
  return {
    id: crypto.randomUUID(),
    created_at: "2026-11-03T09:30:00Z",
    period_start: "2026-11-01",
    period_end: "2026-11-30",
    period_preset: "this_month",
    currency,
    headline: "Income rose 25.1% to 1,250.50 this month.",
    observations: [
      {
        title: "Income grew",
        detail: "Income was 1,250.50, up 25.1% on last month.",
        kind: "positive",
        fact_ids: ["income", "income_change_pct"],
      },
      {
        title: "Cash is running down",
        detail: "At the recent average you have about 6.0 months of cash left.",
        kind: "risk",
        fact_ids: ["cash_runway_months_estimate"],
      },
    ],
    suggestions: [
      {
        title: "Review rent",
        detail: "Rent is your largest expense.",
        fact_ids: ["expense_category_1"],
      },
    ],
    facts: [
      { id: "income", label: "Income this period", value: "1250.5000", unit: "money" },
      {
        id: "income_change_pct",
        label: "Change in income vs previous period",
        value: "25.1",
        unit: "percent",
      },
      {
        id: "cash_runway_months_estimate",
        label: "Estimated months of cash left",
        value: "6.0",
        unit: "months",
      },
      {
        id: "expense_category_1",
        label: "Expense category: Rent & utilities",
        value: "300.0000",
        unit: "money",
      },
    ],
    model: "fake-model",
    ...fields,
  };
}

/** Canned analytics answers. Anything not given is an all-zero report. */
export type FakeAnalytics = { summary?: Summary; cashFlow?: CashFlow; profitLoss?: ProfitLoss };

const OCTOBER = { start: "2026-10-01", end: "2026-10-31", days: 31, preset: null };

export function makeSummary(currency = "USD", fields: Partial<Summary> = {}): Summary {
  const zero = { income: "0.0000", expenses: "0.0000", net: "0.0000", transaction_count: 0 };
  return {
    currency,
    period: { ...OCTOBER, preset: "this_month" },
    previous_period: { start: "2026-09-01", end: "2026-09-30", days: 30, preset: null },
    current: zero,
    previous: zero,
    change: { income_pct: null, expenses_pct: null, net_pct: null },
    cash_balance: "0.0000",
    cash_balance_as_of: "2026-10-31",
    other_currency_transaction_count: 0,
    ...fields,
  };
}

export function makeCashFlow(currency = "USD", fields: Partial<CashFlow> = {}): CashFlow {
  return {
    currency,
    period: OCTOBER,
    granularity: "month",
    opening_balance: "0.0000",
    closing_balance: "0.0000",
    points: [
      {
        start: "2026-10-01",
        end: "2026-10-31",
        income: "0.0000",
        expenses: "0.0000",
        net: "0.0000",
        closing_balance: "0.0000",
      },
    ],
    ...fields,
  };
}

export function makeProfitLoss(currency = "USD", fields: Partial<ProfitLoss> = {}): ProfitLoss {
  const empty = { total: "0.0000", lines: [] };
  return {
    currency,
    period: OCTOBER,
    income: empty,
    expenses: empty,
    net_profit: "0.0000",
    margin_pct: null,
    ...fields,
  };
}

export type FakeOrganization = {
  id: string;
  name: string;
  slug: string;
  base_currency: string;
  fiscal_year_start_month: number;
  created_at: string;
  my_role: OrgRole;
};

/** One organization's ledger: a starter account, two categories and its transactions. */
export type FakeLedger = {
  account: Account;
  sales: Category;
  rent: Category;
  transactions: Transaction[];
};

function makeUser(email: string, fullName: string): FakeUser {
  return {
    id: crypto.randomUUID(),
    email,
    full_name: fullName,
    is_email_verified: false,
    platform_role: "user",
    created_at: "2026-11-03T08:00:00Z",
  };
}

export function makeOrganization(
  name: string,
  baseCurrency = "USD",
  role: OrgRole = "owner",
): FakeOrganization {
  return {
    id: crypto.randomUUID(),
    name,
    slug: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
    base_currency: baseCurrency,
    fiscal_year_start_month: 1,
    created_at: "2026-11-03T08:00:00Z",
    my_role: role,
  };
}

export function makeLedger(currency = "USD"): FakeLedger {
  const category = (name: string, kind: "income" | "expense"): Category => ({
    id: crypto.randomUUID(),
    name,
    kind,
    is_system: true,
    is_archived: false,
  });
  return {
    account: {
      id: crypto.randomUUID(),
      name: "Main account",
      account_type: "bank",
      currency,
      opening_balance: "0.0000",
      is_archived: false,
    },
    sales: category("Sales", "income"),
    rent: category("Rent & utilities", "expense"),
    transactions: [],
  };
}

/** A stored transaction, as the API returns it (amounts with 4 decimal places). */
export function makeTransaction(ledger: FakeLedger, fields: Partial<Transaction>): Transaction {
  return {
    id: crypto.randomUUID(),
    kind: "income",
    amount: "100.0000",
    currency: ledger.account.currency,
    occurred_on: "2026-10-15",
    account_id: ledger.account.id,
    category_id: ledger.sales.id,
    description: "Consulting invoice",
    counterparty: null,
    reference: null,
    created_at: "2026-11-03T08:00:00Z",
    updated_at: "2026-11-03T08:00:00Z",
    ...fields,
  };
}

/** "1250.5" → "1250.5000", like PostgreSQL's NUMERIC(19,4). */
function storedAmount(amount: string): string {
  const [whole, fraction = ""] = amount.split(".");
  return `${whole}.${fraction.padEnd(4, "0")}`;
}

const token = (value: string) => ({ access_token: value, token_type: "bearer", expires_in: 900 });

type Options = {
  signedIn?: boolean;
  organizations?: FakeOrganization[];
  /** Ledgers by organization id. Organizations without one get an empty ledger. */
  ledgers?: Record<string, FakeLedger>;
  /** What POST .../transactions/import answers for a dry run. */
  importReport?: ImportReport;
  analytics?: FakeAnalytics;
  insights?: FakeInsights;
  billing?: Billing;
};

const BILLING_PATH = /^\/api\/v1\/orgs\/([^/]+)\/billing(?:\/(checkout|portal))?$/;
const INSIGHTS_PATH = /^\/api\/v1\/orgs\/([^/]+)\/insights$/;
const REPORTS_PATH = /^\/api\/v1\/orgs\/([^/]+)\/reports\/([a-z-]+\.(?:csv|pdf))$/;
const ANALYTICS_PATH = /^\/api\/v1\/orgs\/([^/]+)\/analytics\/(summary|cash-flow|profit-loss)$/;
const LEDGER_PATH = /^\/api\/v1\/orgs\/([^/]+)\/(accounts|categories|transactions)(?:\/(.+))?$/;

/** A simulated API that follows the real backend's rules for auth, organizations and the ledger. */
export function createFakeBackend({
  signedIn = false,
  organizations = [],
  ledgers = {},
  importReport,
  analytics = {},
  insights = {},
  billing,
}: Options = {}): FetchHandler {
  const amina = makeUser("amina@example.com", "Amina Otieno");
  const accounts = new Map([[amina.email, { password: PASSWORD, user: amina }]]);
  const orgs = [...organizations];
  let current: FakeUser | null = signedIn ? amina : null;
  const insightItems: Record<string, Insight[]> = {};

  function ledgerFor(orgId: string): FakeLedger | undefined {
    const organization = orgs.find((candidate) => candidate.id === orgId);
    if (!organization) return undefined;
    ledgers[orgId] ??= makeLedger(organization.base_currency);
    return ledgers[orgId];
  }

  async function handleLedger(
    request: Request,
    url: URL,
    [, orgId, resource, rest]: RegExpMatchArray,
  ): Promise<Response> {
    const ledger = ledgerFor(orgId);
    if (!ledger) return json(404, { detail: "Organization not found." });

    if (resource === "accounts") return json(200, [ledger.account]);
    if (resource === "categories") return json(200, [ledger.sales, ledger.rent]);

    if (rest === "import") {
      const dryRun = url.searchParams.get("dry_run") === "true";
      const report = importReport ?? {
        status: "validated",
        filename: "bank.csv",
        row_count: 2,
        imported_count: 0,
        error_count: 0,
        errors: [],
      };
      if (dryRun || report.status === "rejected") return json(200, report);
      return json(200, { ...report, status: "imported", imported_count: report.row_count });
    }

    if (rest !== undefined) {
      const index = ledger.transactions.findIndex((item) => item.id === rest);
      if (index === -1) return json(404, { detail: "Transaction not found." });
      if (request.method === "DELETE") {
        ledger.transactions.splice(index, 1);
        return json(204);
      }
      const changes = (await request.json()) as Partial<Transaction>;
      const updated = { ...ledger.transactions[index], ...changes };
      if (changes.amount !== undefined) updated.amount = storedAmount(String(changes.amount));
      ledger.transactions[index] = updated;
      return json(200, updated);
    }

    if (request.method === "POST") {
      const body = (await request.json()) as Partial<Transaction>;
      const created = makeTransaction(ledger, {
        ...body,
        amount: storedAmount(String(body.amount)),
      });
      ledger.transactions.push(created);
      return json(201, created);
    }

    const kind = url.searchParams.get("kind");
    const q = url.searchParams.get("q")?.toLowerCase();
    const page = Number(url.searchParams.get("page") ?? "1");
    const pageSize = Number(url.searchParams.get("page_size") ?? "25");
    const matching = ledger.transactions
      .filter((item) => !kind || item.kind === kind)
      .filter((item) => !q || item.description.toLowerCase().includes(q))
      .sort((a, b) => b.occurred_on.localeCompare(a.occurred_on));
    return json(200, {
      items: matching.slice((page - 1) * pageSize, page * pageSize),
      total: matching.length,
      page,
      page_size: pageSize,
    });
  }

  return async (request) => {
    const url = new URL(request.url);
    const path = url.pathname;
    const authorized = current !== null && request.headers.has("Authorization");

    const billingMatch = BILLING_PATH.exec(path);
    if (billingMatch) {
      if (!authorized) return json(401, { detail: "Not authenticated" });
      const organization = orgs.find((candidate) => candidate.id === billingMatch[1]);
      if (!organization) return json(404, { detail: "Organization not found." });
      const state = billing ?? makeBilling();
      const action = billingMatch[2];
      if (!action) return json(200, state);
      if (organization.my_role !== "owner") {
        return json(403, { detail: "This action requires the owner role or higher." });
      }
      if (action === "portal") {
        return state.status === null
          ? json(409, { detail: "There is no billing account yet. Choose a plan first." })
          : json(200, { url: "https://billing.stripe.com/p/session/test_portal" });
      }
      const body = (await request.json()) as { plan: string };
      return json(200, { url: `https://checkout.stripe.com/c/pay/cs_test_${body.plan}` });
    }

    const insightsMatch = INSIGHTS_PATH.exec(path);
    if (insightsMatch) {
      if (!authorized) return json(401, { detail: "Not authenticated" });
      const organization = orgs.find((candidate) => candidate.id === insightsMatch[1]);
      if (!organization) return json(404, { detail: "Organization not found." });
      const { aiEnabled = true, dailyLimit = 20, failWith } = insights;
      const items = (insightItems[organization.id] ??= [...(insights.existing ?? [])]);
      if (request.method === "POST") {
        if (organization.my_role === "viewer") {
          return json(403, { detail: "This action requires the analyst role or higher." });
        }
        if (!aiEnabled)
          return json(503, { detail: "AI insights are not configured on this server." });
        if (failWith) return json(failWith.status, { detail: failWith.detail });
        const body = (await request.json()) as { period?: string };
        const created = makeInsight(organization.base_currency, {
          period_preset: (body.period ?? "this_month") as Insight["period_preset"],
          created_at: new Date().toISOString(),
        });
        items.unshift(created);
        return json(201, created);
      }
      return json(200, {
        items,
        ai_enabled: aiEnabled,
        daily_limit: dailyLimit,
        remaining_today: Math.max(0, dailyLimit - items.length),
      });
    }

    const reportMatch = REPORTS_PATH.exec(path);
    if (reportMatch) {
      if (!authorized) return json(401, { detail: "Not authenticated" });
      const organization = orgs.find((candidate) => candidate.id === reportMatch[1]);
      if (!organization) return json(404, { detail: "Organization not found." });
      const [name, extension] = reportMatch[2].split(".");
      return new Response(extension === "pdf" ? "%PDF-1.4 fake" : "\ufeffdate,type,amount\r\n", {
        status: 200,
        headers: {
          "Content-Type": extension === "pdf" ? "application/pdf" : "text/csv; charset=utf-8",
          "Content-Disposition": `attachment; filename="${organization.slug}-${name}.${extension}"`,
        },
      });
    }

    const analyticsMatch = ANALYTICS_PATH.exec(path);
    if (analyticsMatch) {
      if (!authorized) return json(401, { detail: "Not authenticated" });
      const organization = orgs.find((candidate) => candidate.id === analyticsMatch[1]);
      if (!organization) return json(404, { detail: "Organization not found." });
      const currency = organization.base_currency;
      if (analyticsMatch[2] === "summary") {
        return json(200, analytics.summary ?? makeSummary(currency));
      }
      if (analyticsMatch[2] === "cash-flow") {
        return json(200, analytics.cashFlow ?? makeCashFlow(currency));
      }
      return json(200, analytics.profitLoss ?? makeProfitLoss(currency));
    }

    const ledgerMatch = LEDGER_PATH.exec(path);
    if (ledgerMatch) {
      if (!authorized) return json(401, { detail: "Not authenticated" });
      return handleLedger(request, url, ledgerMatch);
    }

    switch (path) {
      case "/api/v1/auth/refresh":
        return current
          ? json(200, token("restored"))
          : json(401, { detail: "Session expired. Please log in again." });
      case "/api/v1/auth/login": {
        const body = (await request.json()) as { email: string; password: string };
        const account = accounts.get(body.email);
        if (account?.password !== body.password) {
          return json(401, { detail: "Incorrect email or password." });
        }
        current = account.user;
        return json(200, token("signed-in"));
      }
      case "/api/v1/auth/register": {
        const body = (await request.json()) as {
          email: string;
          password: string;
          full_name: string;
        };
        const user = makeUser(body.email, body.full_name);
        accounts.set(body.email, { password: body.password, user });
        return json(201, user);
      }
      case "/api/v1/auth/me":
        return authorized ? json(200, current) : json(401, { detail: "Not authenticated" });
      case "/api/v1/auth/logout":
        current = null;
        return json(204);
      case "/api/v1/orgs": {
        if (!authorized) return json(401, { detail: "Not authenticated" });
        if (request.method === "GET") return json(200, orgs);
        const body = (await request.json()) as { name: string; base_currency?: string };
        const organization = makeOrganization(body.name, body.base_currency);
        orgs.push(organization);
        return json(201, organization);
      }
      default:
        return json(404, { detail: "Not Found" });
    }
  };
}
