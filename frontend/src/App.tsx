import { useEffect, useState } from "react";

import { apiUrl } from "./lib/config";

// Mirrors HealthResponse in backend/app/schemas/health.py.
// In Phase 3 these types will be generated from the OpenAPI spec automatically.
type Health = {
  status: "ok";
  service: string;
  version: string;
  environment: string;
};

type ApiState =
  { kind: "loading" } | { kind: "ok"; data: Health } | { kind: "error"; message: string };

export default function App() {
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

  const dotColor =
    api.kind === "ok" ? "bg-emerald-400" : api.kind === "error" ? "bg-rose-500" : "bg-amber-400";

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/60 p-8 shadow-2xl">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-500">
          Development build
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Quantova Finance</h1>
        <p className="mt-1 text-sm text-slate-400">AI-powered financial intelligence</p>

        <div className="mt-8 flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3">
          <span className={`h-2.5 w-2.5 rounded-full ${dotColor}`} />
          <span className="text-sm">
            {api.kind === "loading" && "Connecting to API…"}
            {api.kind === "ok" &&
              `API ${api.data.status} · ${api.data.environment} · v${api.data.version}`}
            {api.kind === "error" && `API unreachable (${api.message})`}
          </span>
        </div>
      </div>
    </main>
  );
}
