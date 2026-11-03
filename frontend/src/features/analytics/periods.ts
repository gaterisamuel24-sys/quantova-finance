import type { components } from "../../lib/api/schema";

export type Period = components["schemas"]["Period"];
export type Granularity = components["schemas"]["Granularity"];

/** Named periods, in the order the period picker lists them. */
export const PERIODS: { value: Period; label: string }[] = [
  { value: "this_month", label: "This month" },
  { value: "last_month", label: "Last month" },
  { value: "last_30_days", label: "Last 30 days" },
  { value: "this_quarter", label: "This quarter" },
  { value: "last_quarter", label: "Last quarter" },
  { value: "this_fiscal_year", label: "This financial year" },
  { value: "last_fiscal_year", label: "Last financial year" },
  { value: "last_12_months", label: "Last 12 months" },
];

export const GRANULARITIES: { value: Granularity; label: string }[] = [
  { value: "month", label: "Monthly" },
  { value: "week", label: "Weekly" },
  { value: "day", label: "Daily" },
];

/** Read a period from the URL, falling back to a default for missing or unknown values. */
export function parsePeriod(value: string | null, fallback: Period): Period {
  return PERIODS.find((period) => period.value === value)?.value ?? fallback;
}

export function parseGranularity(value: string | null, fallback: Granularity): Granularity {
  return GRANULARITIES.find((option) => option.value === value)?.value ?? fallback;
}

export function periodLabel(period: Period): string {
  return PERIODS.find((option) => option.value === period)?.label ?? period;
}

const DAY_MONTH = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});
const DAY_MONTH_YEAR = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const MONTH_YEAR = new Intl.DateTimeFormat("en-GB", {
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const MONTH = new Intl.DateTimeFormat("en-GB", { month: "short", timeZone: "UTC" });

// Dates from the API are calendar days without a time, so they are formatted as UTC:
// formatting them in the local time zone could shift them to the previous day.
const asDate = (isoDate: string) => new Date(`${isoDate}T00:00:00Z`);

/** "1 Oct – 31 Oct 2026" */
export function formatRange(start: string, end: string): string {
  return `${DAY_MONTH.format(asDate(start))} – ${DAY_MONTH_YEAR.format(asDate(end))}`;
}

/** Full label for one chart bucket: "Oct 2026", "Week of 5 Oct 2026" or "5 Oct 2026". */
export function bucketLabel(start: string, granularity: Granularity): string {
  if (granularity === "month") return MONTH_YEAR.format(asDate(start));
  if (granularity === "week") return `Week of ${DAY_MONTH_YEAR.format(asDate(start))}`;
  return DAY_MONTH_YEAR.format(asDate(start));
}

/** Short axis label for one chart bucket: "Oct", "5 Oct". */
export function axisLabel(start: string, granularity: Granularity): string {
  return granularity === "month" ? MONTH.format(asDate(start)) : DAY_MONTH.format(asDate(start));
}
