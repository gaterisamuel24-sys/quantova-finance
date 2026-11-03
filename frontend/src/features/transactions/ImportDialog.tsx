import { Download, FileUp } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { Dialog } from "../../components/ui/Dialog";
import { Field } from "../../components/ui/Field";
import { Input } from "../../components/ui/Input";
import { downloadImportTemplate, useImportTransactions, type ImportReport } from "./api";

const MAX_FILE_BYTES = 5 * 1024 * 1024; // the server's limit

type Props = { orgId: string; onClose: () => void };

/**
 * Two-step import: "Check file" asks the server to validate every row without saving
 * anything; only a file with no errors can then be imported, all rows at once.
 */
export function ImportDialog({ orgId, onClose }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const upload = useImportTransactions(orgId);

  function chooseFile(chosen: File | null) {
    setReport(null);
    setError(null);
    if (chosen && chosen.size > MAX_FILE_BYTES) {
      setFile(null);
      setError("The file is larger than 5 MB. Split it into smaller files.");
      return;
    }
    setFile(chosen);
  }

  async function send(dryRun: boolean) {
    if (!file) return;
    setError(null);
    try {
      setReport(await upload.mutateAsync({ file, dryRun }));
    } catch (caught) {
      setReport(null);
      setError(caught instanceof Error ? caught.message : "Could not read the file.");
    }
  }

  async function handleTemplate() {
    setError(null);
    try {
      await downloadImportTemplate(orgId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not download the template.");
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send(true);
  }

  return (
    <Dialog
      title="Import transactions"
      description="Upload a CSV file. Every row is checked first; nothing is saved until you confirm."
      onClose={onClose}
      className="sm:max-w-2xl"
    >
      {report?.status === "imported" ? (
        <div className="grid gap-4">
          <Alert tone="success" title={`Imported ${report.imported_count} transactions.`}>
            They now appear in your transaction list and reports.
          </Alert>
          <div className="flex justify-end">
            <Button data-autofocus onClick={onClose}>
              Done
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="grid gap-4">
          <p className="text-sm text-muted-foreground">
            Required columns:{" "}
            <code className="font-mono text-xs">date, type, amount, description</code>. Optional:{" "}
            <code className="font-mono text-xs">category, account, counterparty, reference</code>.
            Up to 5,000 rows and 5 MB.{" "}
            <button
              type="button"
              onClick={() => void handleTemplate()}
              className="inline-flex items-center gap-1 font-medium text-brand underline-offset-4 hover:underline"
            >
              <Download className="size-3.5" aria-hidden="true" />
              Download the template
            </button>
          </p>

          <Field label="CSV file">
            {(control) => (
              <Input
                data-autofocus
                type="file"
                accept=".csv,text/csv"
                className="h-auto py-2 file:mr-3 file:rounded-md file:border-0 file:bg-surface-muted file:px-3 file:py-1 file:text-sm"
                onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
                {...control}
              />
            )}
          </Field>

          {error && <Alert tone="error" title={error} />}
          {report && <ImportResult report={report} />}

          <div className="mt-2 flex flex-wrap justify-end gap-3">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            {report?.status === "validated" ? (
              <Button loading={upload.isPending} onClick={() => void send(false)}>
                <FileUp className="size-4" aria-hidden="true" />
                Import {report.row_count} transactions
              </Button>
            ) : (
              <Button type="submit" disabled={!file} loading={upload.isPending}>
                Check file
              </Button>
            )}
          </div>
        </form>
      )}
    </Dialog>
  );
}

function ImportResult({ report }: { report: ImportReport }) {
  if (report.status === "validated") {
    return (
      <Alert tone="success" title={`All ${report.row_count} rows are valid.`}>
        Nothing has been saved yet. Choose Import to add them to your ledger.
      </Alert>
    );
  }

  const shown = report.errors.length;
  return (
    <div className="grid gap-3">
      <Alert
        tone="error"
        title={`${report.error_count} ${report.error_count === 1 ? "problem" : "problems"} found in ${report.row_count} rows. Nothing was imported.`}
      >
        Fix them in your file and check it again.
        {report.error_count > shown && ` The first ${shown} are listed.`}
      </Alert>
      <div className="max-h-64 overflow-auto rounded-xl border">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Problems in the file</caption>
          <thead className="sticky top-0 bg-surface-muted text-xs text-muted-foreground">
            <tr>
              <th scope="col" className="px-3 py-2 font-medium">
                Row
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Column
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Problem
              </th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {report.errors.map((issue, index) => (
              <tr key={`${issue.row}-${issue.column ?? ""}-${index}`}>
                <td className="px-3 py-2 font-mono tabular-nums">{issue.row}</td>
                <td className="px-3 py-2 font-mono text-xs">{issue.column ?? "—"}</td>
                <td className="px-3 py-2">{issue.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
