import { useState, type ReactNode } from "react";

import { cn } from "../../lib/cn";
import { formatMoney } from "../../lib/money";
import { compactNumber, labelEvery, niceDomain, plotValue, ticks } from "./scale";

/** One period on a cash-flow chart. Amounts are exact decimal strings from the API. */
export type FlowPoint = {
  key: string;
  /** Full label for tooltips and tables, e.g. "Oct 2026". */
  label: string;
  /** Short axis label, e.g. "Oct". */
  axisLabel: string;
  income: string;
  expenses: string;
  net: string;
  closingBalance: string;
};

// Drawing area in SVG units. The SVG scales to the width of its card.
const WIDTH = 640;
const HEIGHT = 240;
const PAD = { top: 12, right: 8, bottom: 28, left: 48 };
const PLOT_W = WIDTH - PAD.left - PAD.right;
const PLOT_H = HEIGHT - PAD.top - PAD.bottom;

type Scale = { domain: [number, number]; y: (value: number) => number };

function yScale(values: number[]): Scale {
  const domain = niceDomain(values);
  const [low, high] = domain;
  return { domain, y: (value) => PAD.top + PLOT_H - ((value - low) / (high - low)) * PLOT_H };
}

/** A bar whose end away from the baseline is rounded (4px) and whose base is square. */
function barPath(x: number, base: number, end: number, width: number): string {
  const height = Math.abs(base - end);
  if (height === 0) return "";
  const r = Math.min(4, width / 2, height);
  if (end < base) {
    // Grows upwards: round the top corners.
    return `M${x},${base}V${end + r}Q${x},${end} ${x + r},${end}H${x + width - r}Q${x + width},${end} ${x + width},${end + r}V${base}Z`;
  }
  return `M${x},${base}V${end - r}Q${x},${end} ${x + r},${end}H${x + width - r}Q${x + width},${end} ${x + width},${end - r}V${base}Z`;
}

function Grid({ scale }: { scale: Scale }) {
  return (
    <g aria-hidden="true">
      {ticks(scale.domain).map((tick) => (
        <g key={tick}>
          <line
            x1={PAD.left}
            x2={WIDTH - PAD.right}
            y1={scale.y(tick)}
            y2={scale.y(tick)}
            className={tick === 0 ? "stroke-muted-foreground/60" : "stroke-border"}
            strokeWidth={1}
          />
          <text
            x={PAD.left - 8}
            y={scale.y(tick)}
            textAnchor="end"
            dominantBaseline="middle"
            className="fill-muted-foreground text-[11px] tabular-nums"
          >
            {compactNumber(tick)}
          </text>
        </g>
      ))}
    </g>
  );
}

function XLabels({ points, step }: { points: FlowPoint[]; step: number }) {
  const every = labelEvery(points.length);
  return (
    <g aria-hidden="true">
      {points.map((point, index) =>
        index % every === 0 ? (
          <text
            key={point.key}
            x={PAD.left + step * index + step / 2}
            y={HEIGHT - 8}
            textAnchor="middle"
            className="fill-muted-foreground text-[11px]"
          >
            {point.axisLabel}
          </text>
        ) : null,
      )}
    </g>
  );
}

function Tooltip({
  point,
  index,
  count,
  currency,
  children,
}: {
  point: FlowPoint;
  index: number;
  count: number;
  currency: string;
  children: (format: (amount: string) => string) => ReactNode;
}) {
  // Position over the hovered column, flipping to the left half near the right edge.
  const centre = ((PAD.left + (PLOT_W / count) * (index + 0.5)) / WIDTH) * 100;
  const alignRight = centre > 60;
  return (
    <div
      role="status"
      className={cn(
        "pointer-events-none absolute top-2 z-10 min-w-44 rounded-lg border bg-surface px-3 py-2 text-xs shadow-lg",
      )}
      style={alignRight ? { right: `${100 - centre + 2}%` } : { left: `${centre + 2}%` }}
    >
      <p className="mb-1 font-medium text-muted-foreground">{point.label}</p>
      {children((amount) => formatMoney(amount, currency))}
    </div>
  );
}

function TooltipRow({ swatch, label, value }: { swatch?: string; label: string; value: string }) {
  return (
    <p className="flex items-center gap-2">
      {swatch && <span className={cn("h-0.5 w-3 rounded-full", swatch)} aria-hidden="true" />}
      <span className="text-muted-foreground">{label}</span>
      <span className="ml-auto pl-3 font-mono font-semibold text-foreground tabular-nums">
        {value}
      </span>
    </p>
  );
}

export function ChartLegend({ items }: { items: { label: string; swatch: string }[] }) {
  return (
    <ul className="flex flex-wrap gap-4 text-xs text-muted-foreground">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-1.5">
          <span className={cn("size-2.5 rounded-sm", item.swatch)} aria-hidden="true" />
          {item.label}
        </li>
      ))}
    </ul>
  );
}

type ChartProps = { points: FlowPoint[]; currency: string; busy?: boolean };

/** Income and expenses side by side for each period. One axis, starting at zero. */
export function IncomeExpenseBars({ points, currency, busy = false }: ChartProps) {
  const [active, setActive] = useState<number | null>(null);
  if (points.length === 0) return null;

  const scale = yScale(points.flatMap((p) => [plotValue(p.income), plotValue(p.expenses)]));
  const step = PLOT_W / points.length;
  const barWidth = Math.max(2, Math.min(18, (step - 6) / 2));
  const gap = 2; // surface gap between the two bars of a pair
  const base = scale.y(0);
  const activePoint = active === null ? undefined : points[active];

  return (
    <div className={cn("relative transition-opacity", busy && "opacity-60")}>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="h-auto w-full"
        role="group"
        aria-label="Income and expenses by period"
        onMouseLeave={() => setActive(null)}
      >
        <Grid scale={scale} />
        {points.map((point, index) => {
          const centre = PAD.left + step * index + step / 2;
          const incomeX = centre - gap / 2 - barWidth;
          const expenseX = centre + gap / 2;
          return (
            <g key={point.key}>
              <path
                d={barPath(incomeX, base, scale.y(plotValue(point.income)), barWidth)}
                className={cn("fill-chart-income", active === index && "opacity-80")}
              />
              <path
                d={barPath(expenseX, base, scale.y(plotValue(point.expenses)), barWidth)}
                className={cn("fill-chart-expense", active === index && "opacity-80")}
              />
              {/* The hit area is the whole column, much larger than the bars themselves. */}
              <rect
                x={PAD.left + step * index}
                y={PAD.top}
                width={step}
                height={PLOT_H}
                fill="transparent"
                tabIndex={0}
                role="img"
                aria-label={`${point.label}: income ${formatMoney(point.income, currency)}, expenses ${formatMoney(point.expenses, currency)}`}
                className="outline-none focus-visible:stroke-ring focus-visible:stroke-2"
                onMouseEnter={() => setActive(index)}
                onFocus={() => setActive(index)}
                onBlur={() => setActive(null)}
              />
            </g>
          );
        })}
        <XLabels points={points} step={step} />
      </svg>
      {activePoint && active !== null && (
        <Tooltip point={activePoint} index={active} count={points.length} currency={currency}>
          {(format) => (
            <>
              <TooltipRow
                swatch="bg-chart-income"
                label="Income"
                value={format(activePoint.income)}
              />
              <TooltipRow
                swatch="bg-chart-expense"
                label="Expenses"
                value={format(activePoint.expenses)}
              />
              <TooltipRow label="Net" value={format(activePoint.net)} />
            </>
          )}
        </Tooltip>
      )}
    </div>
  );
}

/** Cash balance at the end of each period, as a line. Can go below zero. */
export function BalanceLine({ points, currency, busy = false }: ChartProps) {
  const [active, setActive] = useState<number | null>(null);
  if (points.length === 0) return null;

  const scale = yScale(points.map((p) => plotValue(p.closingBalance)));
  const step = PLOT_W / points.length;
  const x = (index: number) => PAD.left + step * index + step / 2;
  const line = points
    .map(
      (p, index) => `${index === 0 ? "M" : "L"}${x(index)},${scale.y(plotValue(p.closingBalance))}`,
    )
    .join("");
  const activePoint = active === null ? undefined : points[active];

  return (
    <div className={cn("relative transition-opacity", busy && "opacity-60")}>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="h-auto w-full"
        role="group"
        aria-label="Cash balance at the end of each period"
        onMouseLeave={() => setActive(null)}
      >
        <Grid scale={scale} />
        {active !== null && (
          <line
            x1={x(active)}
            x2={x(active)}
            y1={PAD.top}
            y2={PAD.top + PLOT_H}
            className="stroke-muted-foreground/50"
            aria-hidden="true"
          />
        )}
        <path
          d={line}
          fill="none"
          strokeWidth={2}
          strokeLinejoin="round"
          className="stroke-chart-income"
        />
        {activePoint && active !== null && (
          <circle
            cx={x(active)}
            cy={scale.y(plotValue(activePoint.closingBalance))}
            r={4.5}
            strokeWidth={2}
            className="fill-chart-income stroke-surface"
            aria-hidden="true"
          />
        )}
        {points.map((point, index) => (
          <rect
            key={point.key}
            x={PAD.left + step * index}
            y={PAD.top}
            width={step}
            height={PLOT_H}
            fill="transparent"
            tabIndex={0}
            role="img"
            aria-label={`${point.label}: closing balance ${formatMoney(point.closingBalance, currency)}`}
            className="outline-none focus-visible:stroke-ring focus-visible:stroke-2"
            onMouseEnter={() => setActive(index)}
            onFocus={() => setActive(index)}
            onBlur={() => setActive(null)}
          />
        ))}
        <XLabels points={points} step={step} />
      </svg>
      {activePoint && active !== null && (
        <Tooltip point={activePoint} index={active} count={points.length} currency={currency}>
          {(format) => (
            <TooltipRow label="Closing balance" value={format(activePoint.closingBalance)} />
          )}
        </Tooltip>
      )}
    </div>
  );
}

/** The same figures as the charts, as a table: readable without a mouse or without colour. */
export function FlowTable({
  points,
  currency,
  caption,
}: {
  points: FlowPoint[];
  currency: string;
  caption: string;
}) {
  const cell = "px-3 py-2 text-right font-mono tabular-nums";
  return (
    <div className="max-h-80 overflow-auto rounded-xl border">
      <table className="w-full text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="sticky top-0 bg-surface-muted text-xs text-muted-foreground">
          <tr>
            <th scope="col" className="px-3 py-2 text-left font-medium">
              Period
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              Income
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              Expenses
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              Net
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              Closing balance
            </th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {points.map((point) => (
            <tr key={point.key}>
              <th scope="row" className="px-3 py-2 text-left font-normal">
                {point.label}
              </th>
              <td className={cell}>{formatMoney(point.income, currency)}</td>
              <td className={cell}>{formatMoney(point.expenses, currency)}</td>
              <td className={cell}>{formatMoney(point.net, currency)}</td>
              <td className={cell}>{formatMoney(point.closingBalance, currency)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
