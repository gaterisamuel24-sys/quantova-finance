import { useEffect, useState } from "react";

import { api } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";
import { cn } from "../../lib/cn";

type Health = components["schemas"]["HealthResponse"];

type ApiState =
  { kind: "loading" } | { kind: "ok"; data: Health } | { kind: "error"; message: string };

export function ApiStatus() {
  const [api_, setApi] = useState<ApiState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    api
      .GET("/api/v1/health", { signal: controller.signal })
      .then(({ data, response }) => {
        if (data === undefined) throw new Error(`HTTP ${response.status}`);
        setApi({ kind: "ok", data });
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
          api_.kind === "ok" && "bg-positive",
          api_.kind === "error" && "bg-negative",
          api_.kind === "loading" && "bg-warning",
        )}
      />
      <span>
        {api_.kind === "loading" && "Connecting to API…"}
        {api_.kind === "ok" &&
          `API ${api_.data.status} · ${api_.data.environment} · v${api_.data.version}`}
        {api_.kind === "error" && `API unreachable (${api_.message})`}
      </span>
    </div>
  );
}
