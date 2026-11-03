import { Download } from "lucide-react";
import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { downloadFromApi } from "../../lib/api/download";

type Props = {
  /** Text on the button, e.g. "CSV" or "PDF". */
  label: string;
  /** The accessible name, e.g. "Download profit & loss as CSV". */
  description: string;
  path: string;
  query: Record<string, string | undefined>;
  fallbackName: string;
  /** Called with a readable message when the download fails. */
  onError: (message: string | null) => void;
};

export function DownloadButton({ label, description, path, query, fallbackName, onError }: Props) {
  const [busy, setBusy] = useState(false);

  async function handleClick() {
    setBusy(true);
    onError(null);
    try {
      await downloadFromApi(path, query, fallbackName);
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Could not download the file.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button
      variant="secondary"
      loading={busy}
      aria-label={description}
      onClick={() => void handleClick()}
    >
      {!busy && <Download className="size-4" aria-hidden="true" />}
      {label}
    </Button>
  );
}
