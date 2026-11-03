// Axis scaling for charts.
//
// Charts need numbers to work out bar heights and line positions, so amounts are
// converted with Number() here, and only here. That conversion can lose digits past
// about 15 significant figures, which is invisible at chart resolution. Every figure
// shown as text (labels, tooltips, tables) is still formatted from the exact string.

/** A plotting value for an exact amount string. For geometry only, never for arithmetic. */
export function plotValue(amount: string): number {
  const value = Number(amount);
  return Number.isFinite(value) ? value : 0;
}

/** Round up to a "nice" axis maximum: 1, 2, 2.5 or 5 times a power of ten. */
export function niceCeiling(value: number): number {
  if (value <= 0) return 0;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const fraction = value / magnitude;
  const nice =
    fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 2.5 ? 2.5 : fraction <= 5 ? 5 : 10;
  return nice * magnitude;
}

/** An axis range that includes zero and every value, with nice ends. Never empty. */
export function niceDomain(values: number[]): [number, number] {
  const low = Math.min(0, ...values);
  const high = Math.max(0, ...values);
  const lower = low < 0 ? -niceCeiling(-low) : 0;
  const upper = high > 0 ? niceCeiling(high) : 0;
  return lower === upper ? [0, 1] : [lower, upper];
}

/** Evenly spaced tick values across a domain, ends included. */
export function ticks([low, high]: [number, number], count = 4): number[] {
  return Array.from({ length: count + 1 }, (_, index) => low + ((high - low) * index) / count);
}

const COMPACT = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

/** Short axis labels: 0, 500, 1.5K, 2M. */
export function compactNumber(value: number): string {
  return COMPACT.format(value);
}

/** Show at most `max` axis labels by labelling every n-th bucket. */
export function labelEvery(count: number, max = 12): number {
  return Math.max(1, Math.ceil(count / max));
}
