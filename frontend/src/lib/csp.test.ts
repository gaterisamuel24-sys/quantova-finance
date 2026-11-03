import { describe, expect, it } from "vitest";

import indexHtml from "../../index.html?raw";
import { buildContentSecurityPolicy, originOf } from "./csp";

describe("Content Security Policy", () => {
  it("allows scripts only from our own origin, with no inline code or eval", () => {
    const policy = buildContentSecurityPolicy();

    expect(policy).toContain("script-src 'self'");
    expect(policy).not.toContain("unsafe-inline");
    expect(policy).not.toContain("unsafe-eval");
    expect(policy).toContain("object-src 'none'");
    expect(policy).toContain("frame-src 'none'");
  });

  it("lets the app call a separately hosted API, and nothing else", () => {
    const policy = buildContentSecurityPolicy("https://api.quantova.example/some/path");

    expect(policy).toContain("connect-src 'self' https://api.quantova.example;");
  });

  it("refuses an API address that is not http(s)", () => {
    expect(() => originOf("javascript:alert(1)")).toThrow();
  });

  it("index.html has no inline scripts, so the strict policy can apply", () => {
    const inlineScripts = [...indexHtml.matchAll(/<script(?![^>]*\bsrc=)[^>]*>/g)];
    expect(inlineScripts).toEqual([]);
  });
});
