import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  createFakeBackend,
  makeCashFlow,
  makeOrganization,
  makeProfitLoss,
  makeSummary,
  type FakeAnalytics,
} from "../../test/fake-backend";
import { renderRoute } from "../../test/render";

function open(page: string, analytics: FakeAnalytics = {}) {
  const organization = makeOrganization("Acme Ltd", "KES");
  const view = renderRoute(
    `/app/${organization.id}${page}`,
    createFakeBackend({ signedIn: true, organizations: [organization], analytics }),
  );
  return { ...view, organization };
}

const OCTOBER_FIGURES = makeSummary("KES", {
  current: { income: "1250.5000", expenses: "300.2500", net: "950.2500", transaction_count: 3 },
  previous: { income: "1000.0000", expenses: "400.0000", net: "600.0000", transaction_count: 2 },
  change: { income_pct: "25.1", expenses_pct: "-24.9", net_pct: "58.4" },
  cash_balance: "5000.0000",
});

describe("dashboard", () => {
  it("shows exact key figures and how they changed", async () => {
    open("", { summary: OCTOBER_FIGURES });

    const figures = await screen.findByRole("region", { name: "Key figures" });
    await within(figures).findByText("Income");
    expect(figures.textContent).toMatch(/KES\s1,250\.50/);
    expect(figures.textContent).toMatch(/KES\s300\.25/);
    expect(figures.textContent).toMatch(/KES\s5,000\.00/);
    expect(figures.textContent).toContain("Up 25.1%");
    expect(figures.textContent).toContain("Down 24.9%");
  });

  it("says when there is nothing to compare with", async () => {
    open("");

    const figures = await screen.findByRole("region", { name: "Key figures" });
    expect(await within(figures).findAllByText("No earlier figures to compare")).toHaveLength(3);
    expect(await screen.findByText("No transactions in this period")).toBeTruthy();
  });

  it("warns when transactions in another currency are left out", async () => {
    open("", { summary: makeSummary("KES", { other_currency_transaction_count: 2 }) });

    expect(await screen.findByText("Some transactions are not included")).toBeTruthy();
  });

  it("keeps the chosen period in the URL", async () => {
    const { router } = open("");

    fireEvent.change(await screen.findByLabelText("Period"), { target: { value: "last_quarter" } });

    await waitFor(() => expect(router.state.location.search).toBe("?period=last_quarter"));
  });

  it("shows the cash flow chart, with the same figures available as a table", async () => {
    open("", {
      cashFlow: makeCashFlow("KES", {
        points: [
          {
            start: "2026-09-01",
            end: "2026-09-30",
            income: "800.0000",
            expenses: "200.0000",
            net: "600.0000",
            closing_balance: "600.0000",
          },
          {
            start: "2026-10-01",
            end: "2026-10-31",
            income: "1250.5000",
            expenses: "300.2500",
            net: "950.2500",
            closing_balance: "1550.2500",
          },
        ],
      }),
    });

    expect(
      await screen.findByRole("group", { name: "Income and expenses by period" }),
    ).toBeTruthy();
    expect(screen.getByRole("img", { name: /^Oct 2026: income KES\s1,250\.50/ })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Show as table" }));
    const table = screen.getByRole("table", { name: "Cash flow, last 12 months" });
    expect(within(table).getAllByRole("row")).toHaveLength(3);
    expect(table.textContent).toMatch(/KES\s1,550\.25/);
  });
});

describe("profit & loss page", () => {
  it("lists categories, totals, net profit and margin", async () => {
    open("/profit-loss", {
      profitLoss: makeProfitLoss("KES", {
        income: {
          total: "500.0000",
          lines: [
            {
              category_id: crypto.randomUUID(),
              name: "Sales",
              amount: "400.0000",
              transaction_count: 2,
              share_pct: "80.0",
            },
            {
              category_id: null,
              name: "Uncategorized",
              amount: "100.0000",
              transaction_count: 1,
              share_pct: "20.0",
            },
          ],
        },
        expenses: {
          total: "125.0000",
          lines: [
            {
              category_id: crypto.randomUUID(),
              name: "Rent & utilities",
              amount: "125.0000",
              transaction_count: 1,
              share_pct: "100.0",
            },
          ],
        },
        net_profit: "375.0000",
        margin_pct: "75.0",
      }),
    });

    const table = await screen.findByRole("table", { name: /Profit and loss statement/ });
    const netRow = within(table).getByRole("row", { name: /Net profit/ });
    expect(netRow.textContent).toMatch(/KES\s375\.00/);
    expect(within(table).getByRole("row", { name: /Profit margin/ }).textContent).toContain(
      "75.0%",
    );
    expect(within(table).getByRole("row", { name: /^Sales/ }).textContent).toContain("80.0%");
    expect(within(table).getByRole("row", { name: /Total expenses/ }).textContent).toMatch(
      /KES\s125\.00/,
    );
  });

  it("is reachable from the sidebar", async () => {
    open("");

    const nav = await screen.findByRole("navigation", { name: "Workspace" });
    fireEvent.click(within(nav).getByRole("link", { name: "Profit & loss" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Profit & loss" })).toBeTruthy();
  });
});

describe("cash flow page", () => {
  it("shows opening, closing and the exact net change", async () => {
    open("/cash-flow", {
      cashFlow: makeCashFlow("KES", { opening_balance: "0.3000", closing_balance: "0.1000" }),
    });

    const balances = await screen.findByRole("region", { name: "Balances" });
    await within(balances).findByText("Net change");
    // 0.1 − 0.3 is -0.19999999999999998 in floating point; the page shows exactly -0.20.
    expect(balances.textContent).toMatch(/-KES\s0\.20/);
  });
});
