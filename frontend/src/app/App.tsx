import { ArrowDownRight, ArrowUpRight } from "lucide-react";

import { Logo } from "../components/brand/Logo";
import { ThemeToggle } from "../components/ThemeToggle";
import { ApiStatus } from "../features/system/ApiStatus";
import { cn } from "../lib/cn";

// Illustrative figures for the design preview only.
const SAMPLE_METRICS = [
  { label: "Revenue (MTD)", value: "$482,015.00", change: "+12.4%", favorable: true },
  { label: "Operating expenses", value: "$291,540.00", change: "+3.1%", favorable: false },
  { label: "Net cash flow", value: "$190,475.00", change: "+28.9%", favorable: true },
];

const SWATCHES = [
  { name: "background", className: "bg-background" },
  { name: "surface", className: "bg-surface" },
  { name: "surface-muted", className: "bg-surface-muted" },
  { name: "brand", className: "bg-brand" },
  { name: "positive", className: "bg-positive" },
  { name: "negative", className: "bg-negative" },
  { name: "warning", className: "bg-warning" },
];

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b bg-surface/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Logo />
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <p className="text-xs font-medium tracking-[0.2em] text-muted-foreground uppercase">
          Design system preview
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
          Financial clarity, by design.
        </h1>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Semantic tokens drive every colour, so light and dark themes switch instantly. Figures use
          tabular numerals so columns of amounts always align.
        </p>

        <section className="mt-10 grid gap-4 sm:grid-cols-3" aria-label="Sample metrics">
          {SAMPLE_METRICS.map((metric) => (
            <article key={metric.label} className="rounded-2xl border bg-surface p-5 shadow-sm">
              <p className="text-sm text-muted-foreground">{metric.label}</p>
              <p className="mt-2 font-mono text-2xl font-semibold tracking-tight tabular-nums">
                {metric.value}
              </p>
              <p
                className={cn(
                  "mt-3 inline-flex items-center gap-1 text-sm font-medium",
                  metric.favorable ? "text-positive" : "text-negative",
                )}
              >
                {metric.favorable ? (
                  <ArrowUpRight className="size-4" aria-hidden="true" />
                ) : (
                  <ArrowDownRight className="size-4" aria-hidden="true" />
                )}
                {metric.change} vs last month
              </p>
            </article>
          ))}
        </section>

        <section className="mt-10" aria-label="Colour tokens">
          <h2 className="text-sm font-medium text-muted-foreground">Colour tokens</h2>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
            {SWATCHES.map((swatch) => (
              <div key={swatch.name} className="rounded-xl border bg-surface p-2">
                <div className={cn("h-12 rounded-lg border", swatch.className)} />
                <p className="mt-2 font-mono text-xs text-muted-foreground">{swatch.name}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-10 max-w-md" aria-label="Backend status">
          <ApiStatus />
        </section>
      </main>
    </div>
  );
}
