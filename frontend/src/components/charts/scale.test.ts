import { describe, expect, it } from "vitest";

import { compactNumber, labelEvery, niceCeiling, niceDomain, plotValue, ticks } from "./scale";

describe("chart scales", () => {
  it.each([
    [0, 0],
    [7, 10],
    [12, 20],
    [230, 250],
    [4100, 5000],
    [1, 1],
  ])("rounds %d up to the nice value %d", (value, expected) => {
    expect(niceCeiling(value)).toBe(expected);
  });

  it("always includes zero", () => {
    expect(niceDomain([120, 340])).toEqual([0, 500]);
    expect(niceDomain([-30, 80])).toEqual([-50, 100]);
    expect(niceDomain([-30, -10])).toEqual([-50, 0]);
  });

  it("never returns an empty domain", () => {
    expect(niceDomain([])).toEqual([0, 1]);
    expect(niceDomain([0, 0])).toEqual([0, 1]);
  });

  it("spaces ticks evenly", () => {
    expect(ticks([0, 500])).toEqual([0, 125, 250, 375, 500]);
  });

  it("formats axis labels compactly", () => {
    expect(compactNumber(1500)).toBe("1.5K");
    expect(compactNumber(2_000_000)).toBe("2M");
  });

  it("thins out labels on long axes", () => {
    expect(labelEvery(12)).toBe(1);
    expect(labelEvery(31)).toBe(3);
  });

  it("treats malformed amounts as zero for plotting", () => {
    expect(plotValue("1250.5000")).toBe(1250.5);
    expect(plotValue("oops")).toBe(0);
  });
});
