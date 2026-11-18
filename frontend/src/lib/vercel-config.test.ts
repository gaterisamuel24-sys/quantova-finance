// vercel.json must stay in step with the app: the same security policy the build
// produces, and /api forwarded to the backend before the app's catch-all route.
import { describe, expect, it } from "vitest";

import vercelJson from "../../vercel.json?raw";
import { buildContentSecurityPolicy } from "./csp";

type Header = { key: string; value: string };
type VercelConfig = {
  rewrites: { source: string; destination: string }[];
  headers: { source: string; headers: Header[] }[];
};

const config = JSON.parse(vercelJson) as VercelConfig;

describe("vercel.json", () => {
  it("sends the same security policy as the build, plus no framing", () => {
    const appHeaders = config.headers.find((rule) => rule.source === "/((?!api/).*)");
    const csp = appHeaders?.headers.find((header) => header.key === "Content-Security-Policy");

    expect(csp?.value).toBe(`${buildContentSecurityPolicy("")}; frame-ancestors 'none'`);
  });

  it("forwards the API to the backend before falling back to the app", () => {
    const sources = config.rewrites.map((rule) => rule.source);
    const api = config.rewrites.find((rule) => rule.source === "/api/:path*");

    expect(api?.destination).toMatch(/^https:\/\/[^/]+\/api\/:path\*$/);
    expect(sources.indexOf("/api/:path*")).toBeLessThan(sources.indexOf("/(.*)"));
    expect(sources.at(-1)).toBe("/(.*)");
  });
});
