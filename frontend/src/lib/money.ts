// Exact money handling in the browser.
//
// Amounts arrive from the API as strings ("1250.5000") and go back as strings.
// They are never converted to JavaScript numbers, because floating point cannot
// represent most decimal fractions exactly (0.1 + 0.2 !== 0.3).

/** The same limits as the backend: up to 15 digits before the point and 4 after. */
const AMOUNT_PATTERN = /^\d{1,15}(\.\d{1,4})?$/;

export type AmountCheck = { ok: true; value: string } | { ok: false; message: string };

/**
 * Validate what someone typed into an amount field and return the canonical string
 * to send to the API. Spaces and thousands separators ("1,250.50") are accepted.
 */
export function parseAmountInput(input: string): AmountCheck {
  const text = input.replace(/[\s,]/g, "");
  if (text === "") return { ok: false, message: "Enter an amount." };
  if (text.startsWith("-")) {
    return {
      ok: false,
      message: "Enter a positive amount. Choose Expense to record money going out.",
    };
  }
  if (!AMOUNT_PATTERN.test(text)) {
    return { ok: false, message: "Use digits with at most 4 decimal places, e.g. 1250.50" };
  }
  if (/^[0.]+$/.test(text)) return { ok: false, message: "The amount must be more than zero." };
  return { ok: true, value: text };
}

/** Remove trailing zeros the database adds ("1250.5000" → "1250.5"), keeping the value exact. */
export function trimAmount(amount: string): string {
  return amount.includes(".") ? amount.replace(/\.?0+$/, "") : amount;
}

type NumericString = `${number}`;

/** One fixed format everywhere, so figures look the same for every member of a team. */
const MONEY_LOCALE = "en-US";

/**
 * Format an exact decimal string as currency, e.g. ("1250.5", "KES") → "KES 1,250.50".
 * Intl.NumberFormat formats strings exactly (no conversion to a float), so even
 * 15-digit amounts keep every digit.
 */
export function formatMoney(
  amount: string,
  currency: string,
  { signDisplay = "auto" }: { signDisplay?: "auto" | "always" | "exceptZero" } = {},
): string {
  return new Intl.NumberFormat(MONEY_LOCALE, {
    style: "currency",
    currency,
    currencyDisplay: "code",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
    signDisplay,
  }).format(amount as NumericString);
}

const SCALE = 4; // decimal places, as stored by the database

/** An exact decimal string as an integer number of 1/10,000 units. */
function toUnits(amount: string): bigint {
  const text = amount.trim();
  if (!/^[-+]?\d+(\.\d+)?$/.test(text)) throw new Error(`Not a decimal amount: ${amount}`);
  const negative = text.startsWith("-");
  const [whole, fraction = ""] = text.replace(/^[-+]/, "").split(".");
  if (fraction.length > SCALE) throw new Error(`More than ${SCALE} decimal places: ${amount}`);
  const units = BigInt(whole) * 10n ** BigInt(SCALE) + BigInt(fraction.padEnd(SCALE, "0"));
  return negative ? -units : units;
}

function fromUnits(units: bigint): string {
  const negative = units < 0n;
  const digits = (negative ? -units : units).toString().padStart(SCALE + 1, "0");
  const text = `${digits.slice(0, -SCALE)}.${digits.slice(-SCALE)}`;
  return negative ? `-${text}` : text;
}

/** a − b, exactly, using whole-number arithmetic on 1/10,000 units (never floating point). */
export function subtractAmounts(a: string, b: string): string {
  return fromUnits(toUnits(a) - toUnits(b));
}
