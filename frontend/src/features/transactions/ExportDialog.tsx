import { useState } from "react";

import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { Dialog } from "../../components/ui/Dialog";
import { Field } from "../../components/ui/Field";
import { Select } from "../../components/ui/Select";
import { downloadFromApi } from "../../lib/api/download";
import { PERIODS, type Period } from "../analytics/periods";
import type { EntryKind } from "./filters";

type Props = { orgId: string; onClose: () => void };

/** Download transactions as a CSV file that opens directly in Excel or Google Sheets. */
export function ExportDialog({ orgId, onClose }: Props) {
  const [period, setPeriod] = useState<Period>("this_month");
  const [kind, setKind] = useState<EntryKind | "">("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDownload() {
    setBusy(true);
    setError(null);
    try {
      await downloadFromApi(
        `/api/v1/orgs/${encodeURIComponent(orgId)}/reports/transactions.csv`,
        { period, kind: kind || undefined },
        "transactions.csv",
      );
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not download the file.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      title="Export transactions"
      description="A CSV file with one row per transaction, oldest first."
      onClose={onClose}
    >
      <div className="grid gap-4">
        <Field label="Period">
          {(control) => (
            <Select
              data-autofocus
              value={period}
              onChange={(event) => setPeriod(event.target.value as Period)}
              {...control}
            >
              {PERIODS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label="Include">
          {(control) => (
            <Select
              value={kind}
              onChange={(event) => setKind(event.target.value as EntryKind | "")}
              {...control}
            >
              <option value="">Income and expenses</option>
              <option value="income">Income only</option>
              <option value="expense">Expenses only</option>
            </Select>
          )}
        </Field>
        <p className="text-xs text-muted-foreground">
          Text that a spreadsheet could run as a formula is saved with a leading apostrophe, so
          opening the file is always safe. Downloads are recorded in the audit log.
        </p>
        {error && <Alert tone="error" title={error} />}
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={busy} onClick={() => void handleDownload()}>
            Download CSV
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
