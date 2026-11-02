import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ApiStatus } from "./ApiStatus";

function stubFetchResponse(status: number, body: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
    }),
  );
}

describe("ApiStatus", () => {
  it("shows API details when the health check succeeds", async () => {
    stubFetchResponse(200, {
      status: "ok",
      service: "quantova-api",
      version: "0.1.0",
      environment: "test",
    });

    render(<ApiStatus />);

    expect(await screen.findByText("API ok · test · v0.1.0")).toBeTruthy();
    expect(fetch).toHaveBeenCalledWith("/api/v1/health", expect.anything());
  });

  it("shows an error when the API returns a failure status", async () => {
    stubFetchResponse(503, { detail: "unavailable" });

    render(<ApiStatus />);

    expect(await screen.findByText("API unreachable (HTTP 503)")).toBeTruthy();
  });

  it("shows an error when the network request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    render(<ApiStatus />);

    expect(await screen.findByText("API unreachable (Failed to fetch)")).toBeTruthy();
  });
});
