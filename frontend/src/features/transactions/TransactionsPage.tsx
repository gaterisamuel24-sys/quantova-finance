import { ArrowLeftRight, Download, Pencil, Plus, Search, Trash2, Upload } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router";

import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Dialog } from "../../components/ui/Dialog";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Spinner } from "../../components/ui/Spinner";
import { cn } from "../../lib/cn";
import { formatMoney } from "../../lib/money";
import { useCurrentOrganization } from "../organizations/current-organization";
import { canEditLedger } from "../organizations/roles";
import {
  PAGE_SIZE,
  useAccounts,
  useCategories,
  useDeleteTransaction,
  useTransactions,
  type Account,
  type Category,
  type Transaction,
} from "./api";
import {
  EMPTY_FILTERS,
  filtersFromParams,
  filtersToParams,
  hasActiveFilters,
  type TransactionFilters,
} from "./filters";
import { ExportDialog } from "./ExportDialog";
import { ImportDialog } from "./ImportDialog";
import { TransactionFormDialog } from "./TransactionFormDialog";

type OpenDialog =
  | { type: "add" }
  | { type: "edit"; transaction: Transaction }
  | { type: "delete"; transaction: Transaction }
  | { type: "import" }
  | { type: "export" }
  | null;

const DATE_FORMAT = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

/** "2026-11-03" → "3 Nov 2026". The date has no time, so format it as UTC to avoid shifting it. */
function formatDate(isoDate: string): string {
  return DATE_FORMAT.format(new Date(`${isoDate}T00:00:00Z`));
}

export function TransactionsPage() {
  const organization = useCurrentOrganization();
  const orgId = organization.id;
  const canEdit = canEditLedger(organization);
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = filtersFromParams(searchParams);
  const [dialog, setDialog] = useState<OpenDialog>(null);

  const accounts = useAccounts(orgId);
  const categories = useCategories(orgId);
  const transactions = useTransactions(orgId, filters);

  function applyFilters(changes: Partial<TransactionFilters>) {
    // Any new filter starts again from page 1; changing only the page keeps the filters.
    const page = changes.page ?? 1;
    setSearchParams(filtersToParams({ ...filters, ...changes, page }));
  }

  const closeDialog = () => setDialog(null);
  const ready = accounts.data !== undefined && categories.data !== undefined;

  return (
    <>
      <title>{`Transactions · ${organization.name} · Quantova Finance`}</title>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Transactions</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Income and expenses for {organization.name}, in {organization.base_currency}.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setDialog({ type: "export" })}>
            <Download className="size-4" aria-hidden="true" />
            Export CSV
          </Button>
          {canEdit && (
            <>
              <Button variant="secondary" onClick={() => setDialog({ type: "import" })}>
                <Upload className="size-4" aria-hidden="true" />
                Import CSV
              </Button>
              <Button disabled={!ready} onClick={() => setDialog({ type: "add" })}>
                <Plus className="size-4" aria-hidden="true" />
                Add transaction
              </Button>
            </>
          )}
        </div>
      </div>

      <FilterBar
        // Remount when the search changes from outside (back button), so the box shows it.
        key={filters.q}
        filters={filters}
        accounts={accounts.data ?? []}
        categories={categories.data ?? []}
        onChange={applyFilters}
        onClear={() => setSearchParams(filtersToParams(EMPTY_FILTERS))}
      />

      <Card className="mt-4 overflow-hidden">
        {transactions.isPending ? (
          <div className="flex justify-center py-16">
            <Spinner label="Loading transactions" />
          </div>
        ) : transactions.isError ? (
          <div className="grid gap-4 p-5">
            <Alert tone="error" title={transactions.error.message} />
            <Button
              variant="secondary"
              className="w-fit"
              onClick={() => void transactions.refetch()}
            >
              Try again
            </Button>
          </div>
        ) : transactions.data.items.length === 0 ? (
          <EmptyState
            filtered={hasActiveFilters(filters)}
            canEdit={canEdit}
            onAdd={() => setDialog({ type: "add" })}
            onImport={() => setDialog({ type: "import" })}
            onClear={() => setSearchParams(filtersToParams(EMPTY_FILTERS))}
          />
        ) : (
          <>
            <TransactionTable
              items={transactions.data.items}
              accounts={accounts.data ?? []}
              categories={categories.data ?? []}
              canEdit={canEdit}
              busy={transactions.isFetching}
              onEdit={(transaction) => setDialog({ type: "edit", transaction })}
              onDelete={(transaction) => setDialog({ type: "delete", transaction })}
            />
            <Pagination
              page={transactions.data.page}
              total={transactions.data.total}
              onPage={(page) => applyFilters({ page })}
            />
          </>
        )}
      </Card>

      {accounts.data && categories.data && (dialog?.type === "add" || dialog?.type === "edit") && (
        <TransactionFormDialog
          orgId={orgId}
          currency={organization.base_currency}
          accounts={accounts.data}
          categories={categories.data}
          transaction={dialog.type === "edit" ? dialog.transaction : undefined}
          onClose={closeDialog}
        />
      )}
      {dialog?.type === "delete" && (
        <DeleteDialog orgId={orgId} transaction={dialog.transaction} onClose={closeDialog} />
      )}
      {dialog?.type === "import" && <ImportDialog orgId={orgId} onClose={closeDialog} />}
      {dialog?.type === "export" && <ExportDialog orgId={orgId} onClose={closeDialog} />}
    </>
  );
}

// ── Filters ───────────────────────────────────────────

type FilterBarProps = {
  filters: TransactionFilters;
  accounts: Account[];
  categories: Category[];
  onChange: (changes: Partial<TransactionFilters>) => void;
  onClear: () => void;
};

function FilterBar({ filters, accounts, categories, onChange, onClear }: FilterBarProps) {
  const [search, setSearch] = useState(filters.q);
  const visibleCategories = filters.kind
    ? categories.filter((category) => category.kind === filters.kind)
    : categories;

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onChange({ q: search.trim() });
  }

  return (
    <section aria-label="Filters" className="mt-6 grid gap-3">
      <form role="search" onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            type="search"
            aria-label="Search transactions"
            placeholder="Search description, customer, supplier or reference"
            maxLength={100}
            className="pl-9"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Select
          aria-label="Type"
          value={filters.kind}
          onChange={(event) =>
            onChange({ kind: event.target.value as TransactionFilters["kind"], categoryId: "" })
          }
        >
          <option value="">All types</option>
          <option value="income">Income</option>
          <option value="expense">Expenses</option>
        </Select>
        <Select
          aria-label="Account"
          value={filters.accountId}
          onChange={(event) => onChange({ accountId: event.target.value })}
        >
          <option value="">All accounts</option>
          {accounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Category"
          value={filters.categoryId}
          onChange={(event) => onChange({ categoryId: event.target.value })}
        >
          <option value="">All categories</option>
          {visibleCategories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </Select>
        <Input
          type="date"
          aria-label="From date"
          value={filters.dateFrom}
          max={filters.dateTo || undefined}
          onChange={(event) => onChange({ dateFrom: event.target.value })}
        />
        <Input
          type="date"
          aria-label="To date"
          value={filters.dateTo}
          min={filters.dateFrom || undefined}
          onChange={(event) => onChange({ dateTo: event.target.value })}
        />
        <Button
          variant="ghost"
          disabled={!hasActiveFilters(filters)}
          onClick={() => {
            setSearch("");
            onClear();
          }}
        >
          Clear filters
        </Button>
      </div>
    </section>
  );
}

// ── Table ─────────────────────────────────────────────

type TableProps = {
  items: Transaction[];
  accounts: Account[];
  categories: Category[];
  canEdit: boolean;
  busy: boolean;
  onEdit: (transaction: Transaction) => void;
  onDelete: (transaction: Transaction) => void;
};

function TransactionTable({
  items,
  accounts,
  categories,
  canEdit,
  busy,
  onEdit,
  onDelete,
}: TableProps) {
  const accountName = new Map(accounts.map((account) => [account.id, account.name]));
  const categoryName = new Map(categories.map((category) => [category.id, category.name]));
  const cell = "px-4 py-3";

  return (
    <div
      className={cn("overflow-x-auto transition-opacity", busy && "opacity-60")}
      aria-busy={busy}
    >
      <table className="w-full min-w-[44rem] text-left text-sm">
        <caption className="sr-only">Transactions, newest first</caption>
        <thead className="border-b bg-surface-muted/60 text-xs text-muted-foreground">
          <tr>
            <th scope="col" className={cn(cell, "font-medium")}>
              Date
            </th>
            <th scope="col" className={cn(cell, "font-medium")}>
              Description
            </th>
            <th scope="col" className={cn(cell, "font-medium")}>
              Category
            </th>
            <th scope="col" className={cn(cell, "font-medium")}>
              Account
            </th>
            <th scope="col" className={cn(cell, "text-right font-medium")}>
              Amount
            </th>
            {canEdit && (
              <th scope="col" className={cn(cell, "w-24 font-medium")}>
                <span className="sr-only">Actions</span>
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y">
          {items.map((transaction) => {
            const income = transaction.kind === "income";
            const signed = income ? transaction.amount : `-${transaction.amount}`;
            return (
              <tr key={transaction.id} className="hover:bg-surface-muted/40">
                <td className={cn(cell, "whitespace-nowrap text-muted-foreground tabular-nums")}>
                  {formatDate(transaction.occurred_on)}
                </td>
                <td className={cell}>
                  <p className="font-medium">{transaction.description}</p>
                  {(transaction.counterparty || transaction.reference) && (
                    <p className="text-xs text-muted-foreground">
                      {[transaction.counterparty, transaction.reference]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  )}
                </td>
                <td className={cn(cell, "text-muted-foreground")}>
                  {transaction.category_id
                    ? (categoryName.get(transaction.category_id) ?? "Unknown")
                    : "Uncategorized"}
                </td>
                <td className={cn(cell, "text-muted-foreground")}>
                  {accountName.get(transaction.account_id) ?? "Unknown"}
                </td>
                <td
                  className={cn(
                    cell,
                    "text-right font-mono whitespace-nowrap tabular-nums",
                    income ? "text-positive" : "text-foreground",
                  )}
                >
                  <span className="sr-only">{income ? "Income " : "Expense "}</span>
                  {formatMoney(signed, transaction.currency, { signDisplay: "always" })}
                </td>
                {canEdit && (
                  <td className={cn(cell, "py-2")}>
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="px-2"
                        aria-label={`Edit ${transaction.description}`}
                        onClick={() => onEdit(transaction)}
                      >
                        <Pencil className="size-4" aria-hidden="true" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="px-2 hover:text-negative"
                        aria-label={`Delete ${transaction.description}`}
                        onClick={() => onDelete(transaction)}
                      >
                        <Trash2 className="size-4" aria-hidden="true" />
                      </Button>
                    </div>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Pagination({
  page,
  total,
  onPage,
}: {
  page: number;
  total: number;
  onPage: (page: number) => void;
}) {
  const first = (page - 1) * PAGE_SIZE + 1;
  const last = Math.min(page * PAGE_SIZE, total);
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <nav
      aria-label="Pagination"
      className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3 text-sm"
    >
      <p className="text-muted-foreground tabular-nums">
        {first}–{last} of {total}
      </p>
      <div className="flex gap-2">
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={page >= lastPage}
          onClick={() => onPage(page + 1)}
        >
          Next
        </Button>
      </div>
    </nav>
  );
}

function EmptyState({
  filtered,
  canEdit,
  onAdd,
  onImport,
  onClear,
}: {
  filtered: boolean;
  canEdit: boolean;
  onAdd: () => void;
  onImport: () => void;
  onClear: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-4 py-16 text-center">
      <ArrowLeftRight className="size-6 text-muted-foreground" aria-hidden="true" />
      <p className="font-medium">
        {filtered ? "No transactions match these filters" : "No transactions yet"}
      </p>
      <p className="max-w-sm text-sm text-muted-foreground">
        {filtered
          ? "Try a different search or date range."
          : canEdit
            ? "Add your first transaction, or import a CSV file from your bank or spreadsheet."
            : "Transactions added by your team will appear here."}
      </p>
      <div className="mt-2 flex gap-2">
        {filtered ? (
          <Button variant="secondary" onClick={onClear}>
            Clear filters
          </Button>
        ) : (
          canEdit && (
            <>
              <Button variant="secondary" onClick={onImport}>
                Import CSV
              </Button>
              <Button onClick={onAdd}>Add transaction</Button>
            </>
          )
        )}
      </div>
    </div>
  );
}

// ── Delete ────────────────────────────────────────────

function DeleteDialog({
  orgId,
  transaction,
  onClose,
}: {
  orgId: string;
  transaction: Transaction;
  onClose: () => void;
}) {
  const remove = useDeleteTransaction(orgId);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setError(null);
    try {
      await remove.mutateAsync(transaction.id);
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete the transaction.");
    }
  }

  return (
    <Dialog title="Delete this transaction?" onClose={onClose}>
      <div className="grid gap-4">
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{transaction.description}</span> (
          {formatMoney(transaction.amount, transaction.currency)},{" "}
          {formatDate(transaction.occurred_on)}) will be removed from your ledger and reports. A
          record of the deletion is kept in the audit log.
        </p>
        {error && <Alert tone="error" title={error} />}
        <div className="flex justify-end gap-3">
          <Button variant="ghost" data-autofocus onClick={onClose}>
            Cancel
          </Button>
          <Button variant="danger" loading={remove.isPending} onClick={() => void confirm()}>
            Delete
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
