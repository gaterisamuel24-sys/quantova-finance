import { describe, expect, it } from "vitest";

import { safeRedirect } from "./redirect";

describe("safeRedirect", () => {
  it.each([
    [{ from: "/app/reports?period=q1" }, "/app/reports?period=q1"],
    [{ from: "https://evil.example" }, "/app"],
    [{ from: "//evil.example/login" }, "/app"],
    [{ from: 42 }, "/app"],
    [null, "/app"],
  ])("safeRedirect(%j) -> %s", (state, expected) => {
    expect(safeRedirect(state)).toBe(expected);
  });
});
