import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { FetchHandler } from "../../test/fake-api";
import {
  createFakeBackend,
  makeLedger,
  makeOrganization,
  makeTransaction,
  type FakeLedger,
  type FakeOrganization,
} from "../../test/fake-backend";
import { renderRoute } from "../../test/render";
import type { ImportReport } from "./api";

type Setup = {
  role?: FakeOrganization["my_role"];
  seed?: (ledger: FakeLedger) => void;
  importReport?: ImportReport;
};

/** Open the transactions page of a fresh organization, recording every JSON body sent. */
function openTransactions({ role = "owner", seed, importReport }: Setup = {}) {
  const organization = makeOrganization("Acme Ltd", "USD", role);
  const ledger = makeLedger("USD");
  seed?.(ledger);
  const backend = createFakeBackend({
    signedIn: true,
    organizations: [organization],
    ledgers: { [organization.id]: ledger },
    importReport,
  });

  const sent: { method: string; path: string; body: unknown }[] = [];
  const recording: FetchHandler = async (request) => {
    if (
      (request.method === "POST" || request.method === "PATCH") &&
      new URL(request.url).pathname.includes("/transactions")
    ) {
      const type = request.headers.get("Content-Type") ?? "";
      const body: unknown = type.includes("json") ? await request.clone().json() : null;
      sent.push({ method: request.method, path: new URL(request.url).pathname, body });
    }
    return backend(request);
  };

  const view = renderRoute(`/app/${organization.id}/transactions`, recording);
  return { ...view, ledger, sent };
}

const table = () => screen.findByRole("table");
const dialog = (name: string) => screen.findByRole("dialog", { name });

describe("transactions page", () => {
  it("lists transactions with exact, signed amounts", async () => {
    openTransactions({
      seed: (ledger) =>
        ledger.transactions.push(
          makeTransaction(ledger, { amount: "1250.5000", description: "Invoice #1042" }),
          makeTransaction(ledger, {
            kind: "expense",
            amount: "300.0000",
            category_id: ledger.rent.id,
            description: "Office rent",
          }),
        ),
    });

    const rows = within(await table()).getAllByRole("row");
    expect(rows).toHaveLength(3); // header + 2 transactions
    expect(rows[1].textContent).toContain("Invoice #1042");
    expect(rows[1].textContent).toMatch(/\+USD\s1,250\.50/);
    expect(rows[2].textContent).toContain("Rent & utilities");
    expect(rows[2].textContent).toMatch(/-USD\s300\.00/);
  });

  it("adds a transaction, sending the amount as an exact string", async () => {
    const { sent } = openTransactions();

    expect(await screen.findByText("No transactions yet")).toBeTruthy();
    fireEvent.click(screen.getAllByRole("button", { name: "Add transaction" })[0]);
    const form = within(await dialog("Add transaction"));
    fireEvent.change(form.getByLabelText("Amount"), { target: { value: "1,250.50" } });
    fireEvent.change(form.getByLabelText("Description"), { target: { value: "Office rent" } });
    fireEvent.click(form.getByRole("button", { name: "Add transaction" }));

    expect(within(await table()).getByText("Office rent")).toBeTruthy();
    const created = sent.find((call) => call.method === "POST");
    expect(created?.body).toMatchObject({ kind: "expense", amount: "1250.50" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("rejects an inexact amount before contacting the server", async () => {
    const { sent } = openTransactions();

    expect(await screen.findByText("No transactions yet")).toBeTruthy();
    fireEvent.click(screen.getAllByRole("button", { name: "Add transaction" })[0]);
    const form = within(await dialog("Add transaction"));
    fireEvent.change(form.getByLabelText("Amount"), { target: { value: "10.12345" } });
    fireEvent.change(form.getByLabelText("Description"), { target: { value: "Too precise" } });
    fireEvent.click(form.getByRole("button", { name: "Add transaction" }));

    expect(await form.findByText(/at most 4 decimal places/)).toBeTruthy();
    expect(sent).toHaveLength(0);
  });

  it("edits only the fields that changed", async () => {
    const { sent } = openTransactions({
      seed: (ledger) => ledger.transactions.push(makeTransaction(ledger, { description: "Typo" })),
    });

    fireEvent.click(within(await table()).getByRole("button", { name: "Edit Typo" }));
    const form = within(await dialog("Edit transaction"));
    expect((form.getByLabelText("Amount") as HTMLInputElement).value).toBe("100");
    fireEvent.change(form.getByLabelText("Description"), { target: { value: "Fixed" } });
    fireEvent.click(form.getByRole("button", { name: "Save changes" }));

    expect(await within(await table()).findByText("Fixed")).toBeTruthy();
    await waitFor(() => expect(sent.find((call) => call.method === "PATCH")).toBeTruthy());
    expect(sent.find((call) => call.method === "PATCH")?.body).toEqual({ description: "Fixed" });
  });

  it("deletes a transaction after confirmation", async () => {
    openTransactions({
      seed: (ledger) =>
        ledger.transactions.push(makeTransaction(ledger, { description: "Duplicate" })),
    });

    fireEvent.click(within(await table()).getByRole("button", { name: "Delete Duplicate" }));
    fireEvent.click(
      within(await dialog("Delete this transaction?")).getByRole("button", { name: "Delete" }),
    );

    expect(await screen.findByText("No transactions yet")).toBeTruthy();
  });

  it("filters by type through the URL", async () => {
    const { router } = openTransactions({
      seed: (ledger) =>
        ledger.transactions.push(
          makeTransaction(ledger, { description: "Sale" }),
          makeTransaction(ledger, { kind: "expense", category_id: null, description: "Fuel" }),
        ),
    });

    expect(within(await table()).getByText("Fuel")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Type"), { target: { value: "income" } });

    await waitFor(() => expect(screen.queryByText("Fuel")).toBeNull());
    expect(router.state.location.search).toBe("?kind=income");
    expect(within(await table()).getByText("Sale")).toBeTruthy();
  });

  it("is read-only for viewers", async () => {
    openTransactions({
      role: "viewer",
      seed: (ledger) => ledger.transactions.push(makeTransaction(ledger, { description: "Sale" })),
    });

    expect(within(await table()).getByText("Sale")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Add transaction" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Import CSV" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Edit Sale" })).toBeNull();
  });
});

describe("CSV import", () => {
  const csv = () => new File(["date,type,amount,description\n"], "bank.csv", { type: "text/csv" });

  async function chooseFileAndCheck() {
    // An empty ledger shows "Import CSV" twice: in the header and in the empty state.
    fireEvent.click((await screen.findAllByRole("button", { name: "Import CSV" }))[0]);
    const importDialog = within(await dialog("Import transactions"));
    fireEvent.change(importDialog.getByLabelText("CSV file"), { target: { files: [csv()] } });
    fireEvent.click(importDialog.getByRole("button", { name: "Check file" }));
    return importDialog;
  }

  it("previews a valid file, then imports it", async () => {
    openTransactions();

    const importDialog = await chooseFileAndCheck();
    expect(await importDialog.findByText("All 2 rows are valid.")).toBeTruthy();
    fireEvent.click(importDialog.getByRole("button", { name: "Import 2 transactions" }));

    expect(await importDialog.findByText("Imported 2 transactions.")).toBeTruthy();
  });

  it("lists the problems in a rejected file and imports nothing", async () => {
    openTransactions({
      importReport: {
        status: "rejected",
        filename: "bank.csv",
        row_count: 3,
        imported_count: 0,
        error_count: 1,
        errors: [{ row: 3, column: "amount", message: "Amount must be a positive number" }],
      },
    });

    const importDialog = await chooseFileAndCheck();

    expect(await importDialog.findByText(/1 problem found in 3 rows/)).toBeTruthy();
    expect(importDialog.getByText("Amount must be a positive number")).toBeTruthy();
    expect(importDialog.queryByRole("button", { name: /^Import \d/ })).toBeNull();
  });
});
