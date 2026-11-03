import { useState, type FormEvent } from "react";

import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { Dialog } from "../../components/ui/Dialog";
import { Field } from "../../components/ui/Field";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { ApiRequestError } from "../../lib/api/errors";
import { cn } from "../../lib/cn";
import { parseAmountInput, trimAmount } from "../../lib/money";
import {
  useCreateTransaction,
  useUpdateTransaction,
  type Account,
  type Category,
  type Transaction,
  type TransactionUpdate,
} from "./api";
import { todayIso, type EntryKind } from "./filters";

type FormValues = {
  kind: EntryKind;
  amount: string;
  occurredOn: string;
  accountId: string;
  categoryId: string;
  description: string;
  counterparty: string;
  reference: string;
};

type Props = {
  orgId: string;
  currency: string;
  accounts: Account[];
  categories: Category[];
  /** The transaction to edit, or undefined to add a new one. */
  transaction?: Transaction;
  onClose: () => void;
};

function initialValues(accounts: Account[], transaction?: Transaction): FormValues {
  if (transaction) {
    return {
      kind: transaction.kind,
      amount: trimAmount(transaction.amount),
      occurredOn: transaction.occurred_on,
      accountId: transaction.account_id,
      categoryId: transaction.category_id ?? "",
      description: transaction.description,
      counterparty: transaction.counterparty ?? "",
      reference: transaction.reference ?? "",
    };
  }
  return {
    kind: "expense",
    amount: "",
    occurredOn: todayIso(),
    accountId: accounts.find((account) => !account.is_archived)?.id ?? "",
    categoryId: "",
    description: "",
    counterparty: "",
    reference: "",
  };
}

/** The request body: only fields that changed when editing, and amounts as exact strings. */
function toPayload(values: FormValues, amount: string) {
  return {
    kind: values.kind,
    amount,
    occurred_on: values.occurredOn,
    account_id: values.accountId,
    category_id: values.categoryId || null,
    description: values.description.trim(),
    counterparty: values.counterparty.trim() || null,
    reference: values.reference.trim() || null,
  };
}

function changedFields(transaction: Transaction, payload: ReturnType<typeof toPayload>) {
  const original = toPayload(initialValues([], transaction), trimAmount(transaction.amount));
  const changes: TransactionUpdate = {};
  for (const key of Object.keys(payload) as (keyof typeof payload)[]) {
    if (payload[key] !== original[key]) Object.assign(changes, { [key]: payload[key] });
  }
  return changes;
}

export function TransactionFormDialog({
  orgId,
  currency,
  accounts,
  categories,
  transaction,
  onClose,
}: Props) {
  const isEdit = transaction !== undefined;
  const [values, setValues] = useState(() => initialValues(accounts, transaction));
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const create = useCreateTransaction(orgId);
  const update = useUpdateTransaction(orgId);
  const saving = create.isPending || update.isPending;

  const kindCategories = categories.filter(
    (category) =>
      category.kind === values.kind && (!category.is_archived || category.id === values.categoryId),
  );
  const selectableAccounts = accounts.filter(
    (account) => !account.is_archived || account.id === values.accountId,
  );

  function set<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function setKind(kind: EntryKind) {
    // A category belongs to one kind, so switching kind clears a category that no longer fits.
    setValues((current) => {
      const stillFits = categories.some(
        (category) => category.id === current.categoryId && category.kind === kind,
      );
      return { ...current, kind, categoryId: stillFits ? current.categoryId : "" };
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    const amount = parseAmountInput(values.amount);
    if (!amount.ok) {
      setFieldErrors({ amount: amount.message });
      return;
    }
    setFieldErrors({});
    const payload = toPayload(values, amount.value);

    try {
      if (transaction) {
        const changes = changedFields(transaction, payload);
        if (Object.keys(changes).length > 0) {
          await update.mutateAsync({ id: transaction.id, changes });
        }
      } else {
        await create.mutateAsync(payload);
      }
      onClose();
    } catch (caught) {
      if (caught instanceof ApiRequestError && Object.keys(caught.fieldErrors).length > 0) {
        setFieldErrors(caught.fieldErrors);
      } else {
        setFormError(caught instanceof Error ? caught.message : "Could not save the transaction.");
      }
    }
  }

  return (
    <Dialog
      title={isEdit ? "Edit transaction" : "Add transaction"}
      description={`Amounts are in ${currency}.`}
      onClose={onClose}
    >
      <form onSubmit={(event) => void handleSubmit(event)} className="grid gap-4" noValidate>
        {formError && <Alert tone="error" title={formError} />}

        <fieldset className="grid gap-1.5">
          <legend className="mb-1.5 text-sm font-medium">Type</legend>
          <div className="grid grid-cols-2 gap-2">
            {(["expense", "income"] as const).map((kind) => (
              <label
                key={kind}
                className={cn(
                  "flex h-10 cursor-pointer items-center justify-center rounded-lg border text-sm font-medium capitalize",
                  "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-ring",
                  values.kind === kind &&
                    (kind === "income"
                      ? "border-positive bg-positive/10 text-positive"
                      : "border-negative bg-negative/10 text-negative"),
                )}
              >
                <input
                  type="radio"
                  name="kind"
                  value={kind}
                  checked={values.kind === kind}
                  onChange={() => setKind(kind)}
                  className="sr-only"
                />
                {kind}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Amount" error={fieldErrors.amount}>
            {(control) => (
              <Input
                data-autofocus
                inputMode="decimal"
                autoComplete="off"
                placeholder="0.00"
                className="font-mono tabular-nums"
                value={values.amount}
                onChange={(event) => set("amount", event.target.value)}
                {...control}
              />
            )}
          </Field>
          <Field label="Date" error={fieldErrors.occurred_on}>
            {(control) => (
              <Input
                type="date"
                required
                value={values.occurredOn}
                onChange={(event) => set("occurredOn", event.target.value)}
                {...control}
              />
            )}
          </Field>
        </div>

        <Field label="Description" error={fieldErrors.description}>
          {(control) => (
            <Input
              required
              maxLength={500}
              placeholder={values.kind === "income" ? "Invoice #1042" : "Office rent, November"}
              value={values.description}
              onChange={(event) => set("description", event.target.value)}
              {...control}
            />
          )}
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Account" error={fieldErrors.account_id}>
            {(control) => (
              <Select
                required
                value={values.accountId}
                onChange={(event) => set("accountId", event.target.value)}
                {...control}
              >
                {selectableAccounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field label="Category" error={fieldErrors.category_id}>
            {(control) => (
              <Select
                value={values.categoryId}
                onChange={(event) => set("categoryId", event.target.value)}
                {...control}
              >
                <option value="">Uncategorized</option>
                {kindCategories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label={values.kind === "income" ? "Customer (optional)" : "Supplier (optional)"}
            error={fieldErrors.counterparty}
          >
            {(control) => (
              <Input
                maxLength={200}
                value={values.counterparty}
                onChange={(event) => set("counterparty", event.target.value)}
                {...control}
              />
            )}
          </Field>
          <Field label="Reference (optional)" error={fieldErrors.reference}>
            {(control) => (
              <Input
                maxLength={100}
                placeholder="INV-1042"
                value={values.reference}
                onChange={(event) => set("reference", event.target.value)}
                {...control}
              />
            )}
          </Field>
        </div>

        <div className="mt-2 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            {isEdit ? "Save changes" : "Add transaction"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
