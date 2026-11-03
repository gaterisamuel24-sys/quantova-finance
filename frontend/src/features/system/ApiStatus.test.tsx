import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ApiStatus } from "./ApiStatus";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("ApiStatus", () => {
  it("shows API details when the health check succeeds", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        status: "ok",
        service: "quantova-api",
        version: "0.1.0",
        environment: "test",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ApiStatus />);

    expect(await screen.findByText("API ok · test · v0.1.0")).toBeTruthy();
    const request = fetchMock.mock.calls[0][0] as Request;
    expect(new URL(request.url).pathname).toBe("/api/v1/health");
  });

  it("shows an error when the API returns a failure status", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(503, { detail: "down" })));

    render(<ApiStatus />);

    expect(await screen.findByText("API unreachable (HTTP 503)")).toBeTruthy();
  });

  it("shows an error when the network request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    render(<ApiStatus />);

    expect(await screen.findByText("API unreachable (Failed to fetch)")).toBeTruthy();
  });
});
