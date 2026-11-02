import { useEffect, useState } from "react";

import { cn } from "../../lib/cn";
import { apiUrl } from "../../lib/config";

// Mirrors HealthResponse in backend/app/schemas/health.py (generated types arrive in step 3.2).
type Health = {
  status: "ok";
  service: string;
  version: string;
  environment: string;
};

type ApiState =
  { kind: "loading" } | { kind: "ok"; data: Health } | { kind: "error"; message: string };

export function ApiStatus() {
  const [api, setApi] = useState<ApiState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    fetch(apiUrl("/api/v1/health"), { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        setApi({ kind: "ok", data: (await response.json()) as Health });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setApi({
          kind: "error",
          message: error instanceof Error ? error.message : "Unknown error",
        });
      });

    return () => controller.abort();
  }, []);

  return (
    <div className="flex items-center gap-3 rounded-xl border bg-surface px-4 py-3 text-sm">
      <span
        className={cn(
          "size-2.5 rounded-full",
          api.kind === "ok" && "bg-positive",
          api.kind === "error" && "bg-negative",
          api.kind === "loading" && "bg-warning",
        )}
      />
      <span>
        {api.kind === "loading" && "Connecting to API…"}
        {api.kind === "ok" &&
          `API ${api.data.status} · ${api.data.environment} · v${api.data.version}`}
        {api.kind === "error" && `API unreachable (${api.message})`}
      </span>
    </div>
  );
}
