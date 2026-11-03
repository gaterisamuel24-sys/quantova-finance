import { Minus, TrendingDown, TrendingUp } from "lucide-react";

import { Card } from "../../components/ui/Card";
import { cn } from "../../lib/cn";
import { formatMoney } from "../../lib/money";
import type { CashFlow } from "./api";
import { axisLabel, bucketLabel } from "./periods";
import type { FlowPoint } from "../../components/charts/CashFlowCharts";

type Change = {
  /** Percentage change from the API ("12.5", "-3.0"), or null when there is no baseline. */
  pct: string | null;
  /** Whether a rise is good news (income) or bad news (expenses). */
  higherIsBetter: boolean;
};

type StatTileProps = {
  label: string;
  amount: string;
  currency: string;
  change?: Change;
  footnote?: string;
};

function ChangeLine({ pct, higherIsBetter }: Change) {
  if (pct === null) {
    return <p className="mt-3 text-xs text-muted-foreground">No earlier figures to compare</p>;
  }
  const direction = pct.startsWith("-") ? "down" : /^0(\.0+)?$/.test(pct) ? "flat" : "up";
  const good = direction === "flat" ? null : (direction === "up") === higherIsBetter;
  const Icon = direction === "up" ? TrendingUp : direction === "down" ? TrendingDown : Minus;
  const size = pct.replace(/^-/, "");

  return (
    <p
      className={cn(
        "mt-3 flex items-center gap-1 text-xs font-medium",
        good === null ? "text-muted-foreground" : good ? "text-positive" : "text-negative",
      )}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {/* Words as well as colour and icon, so the meaning never depends on colour alone. */}
      {direction === "flat" ? "No change" : `${direction === "up" ? "Up" : "Down"} ${size}%`}
      <span className="font-normal text-muted-foreground">vs previous period</span>
    </p>
  );
}

/** One headline figure: a label, an exact amount and how it changed. */
export function StatTile({ label, amount, currency, change, footnote }: StatTileProps) {
  return (
    <Card className="p-5">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-2 font-mono text-2xl font-semibold tracking-tight tabular-nums">
        {formatMoney(amount, currency)}
      </p>
      {change && <ChangeLine {...change} />}
      {footnote && <p className="mt-3 text-xs text-muted-foreground">{footnote}</p>}
    </Card>
  );
}

/** Turn a cash-flow response into chart points. */
export function toFlowPoints(cashFlow: CashFlow): FlowPoint[] {
  return cashFlow.points.map((point) => ({
    key: point.start,
    label: bucketLabel(point.start, cashFlow.granularity),
    axisLabel: axisLabel(point.start, cashFlow.granularity),
    income: point.income,
    expenses: point.expenses,
    net: point.net,
    closingBalance: point.closing_balance,
  }));
}
