import { ArrowDownRight, ArrowUpRight, Sparkles } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import { cn } from "../../lib/cn";

// Illustrative sample data. Labelled as such below the preview.
const KPIS = [
  { label: "Cash balance", value: "$1,284,300", change: "+4.2%", favorable: true },
  { label: "Net profit (Q1)", value: "$212,940", change: "+9.8%", favorable: true },
  { label: "Monthly burn", value: "$86,410", change: "-6.1%", favorable: true },
];

const LINE =
  "M0,150 C50,142 80,122 120,126 S200,92 240,97 S320,72 360,82 S440,52 480,57 S560,32 600,36";

export function HeroPreview() {
  return (
    <figure className="relative">
      <div className="absolute -inset-6 -z-10 rounded-[2rem] bg-brand/15 blur-3xl" />
      <div
        role="img"
        aria-label="Illustration of the Quantova dashboard showing sample cash, profit and burn figures with a cash flow chart and an AI insight"
        className="rounded-2xl border bg-surface p-4 shadow-xl sm:p-6"
      >
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium">Cash flow · last 12 months</p>
          <Badge tone="brand">Live</Badge>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-2 sm:gap-3">
          {KPIS.map((kpi) => (
            <div key={kpi.label} className="rounded-xl border bg-background p-2.5 sm:p-3">
              <p className="truncate text-[11px] text-muted-foreground sm:text-xs">{kpi.label}</p>
              <p className="mt-1 truncate font-mono text-sm font-semibold tabular-nums sm:text-base">
                {kpi.value}
              </p>
              <p
                className={cn(
                  "mt-1 inline-flex items-center gap-0.5 text-[11px] font-medium sm:text-xs",
                  kpi.favorable ? "text-positive" : "text-negative",
                )}
              >
                {kpi.change.startsWith("-") ? (
                  <ArrowDownRight className="size-3" />
                ) : (
                  <ArrowUpRight className="size-3" />
                )}
                {kpi.change}
              </p>
            </div>
          ))}
        </div>

        <svg viewBox="0 0 600 200" className="mt-4 h-36 w-full sm:h-44" preserveAspectRatio="none">
          <defs>
            <linearGradient id="hero-area" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" style={{ stopColor: "var(--brand)", stopOpacity: 0.3 }} />
              <stop offset="100%" style={{ stopColor: "var(--brand)", stopOpacity: 0 }} />
            </linearGradient>
          </defs>
          {[50, 100, 150].map((y) => (
            <line key={y} x1="0" x2="600" y1={y} y2={y} className="stroke-border" strokeWidth="1" />
          ))}
          <path d={`${LINE} L600,200 L0,200 Z`} fill="url(#hero-area)" />
          <path d={LINE} fill="none" className="stroke-brand" strokeWidth="3" />
        </svg>

        <div className="mt-4 flex gap-3 rounded-xl border bg-background p-3 text-sm">
          <Sparkles className="mt-0.5 size-4 shrink-0 text-brand" />
          <p className="text-muted-foreground">
            <span className="font-medium text-foreground">Insight:</span> Net profit rose 9.8% this
            quarter, mainly from consulting revenue. Operating costs held steady.
          </p>
        </div>
      </div>
      <figcaption className="mt-3 text-center text-xs text-muted-foreground">
        Illustrative sample data
      </figcaption>
    </figure>
  );
}
