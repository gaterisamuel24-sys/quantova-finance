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
};

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
}: Options = {}): FetchHandler {
  const amina = makeUser("amina@example.com", "Amina Otieno");
  const accounts = new Map([[amina.email, { password: PASSWORD, user: amina }]]);
  const orgs = [...organizations];
  let current: FakeUser | null = signedIn ? amina : null;

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
