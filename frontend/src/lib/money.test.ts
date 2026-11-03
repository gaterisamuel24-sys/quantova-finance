import { describe, expect, it } from "vitest";

import { formatMoney, parseAmountInput, trimAmount } from "./money";

describe("parseAmountInput", () => {
  it.each([
    ["1250.50", "1250.50"],
    [" 1,250.5 ", "1250.5"],
    ["0.0001", "0.0001"],
    ["999999999999999.9999", "999999999999999.9999"],
  ])("accepts %j as %j", (input, expected) => {
    expect(parseAmountInput(input)).toEqual({ ok: true, value: expected });
  });

  it.each(["", "abc", "1.23456", "1e3", "12.", ".5", "0", "0.00", "-5", "1234567890123456"])(
    "rejects %j",
    (input) => {
      expect(parseAmountInput(input).ok).toBe(false);
    },
  );

  it("explains how to record money going out", () => {
    const result = parseAmountInput("-20");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.message).toContain("Expense");
  });
});

describe("trimAmount", () => {
  it.each([
    ["1250.5000", "1250.5"],
    ["1250.0000", "1250"],
    ["1250", "1250"],
    ["0.1000", "0.1"],
  ])("trims %j to %j", (input, expected) => {
    expect(trimAmount(input)).toBe(expected);
  });
});

describe("formatMoney", () => {
  it("keeps every digit of large amounts", () => {
    // As a JavaScript number this would round to 1234567890123456.8.
    expect(formatMoney("123456789012345.6789", "USD")).toContain("123,456,789,012,345.6789");
  });

  it("shows at least two decimals and the currency code", () => {
    const text = formatMoney("1250.5", "KES");
    expect(text).toContain("1,250.50");
    expect(text).toContain("KES");
  });

  it("can always show the sign", () => {
    expect(formatMoney("10", "USD", { signDisplay: "always" })).toContain("+");
    expect(formatMoney("-10", "USD", { signDisplay: "always" })).toContain("-");
  });
});
