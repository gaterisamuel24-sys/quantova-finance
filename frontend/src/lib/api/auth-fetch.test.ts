import { beforeEach, describe, expect, it, vi } from "vitest";

import { API_ORIGIN } from "../config";
import { authFetch } from "./auth-fetch";
import { tokenStore } from "./token-store";

const ORGS_URL = `${API_ORIGIN}/api/v1/orgs`;
const LOGIN_URL = `${API_ORIGIN}/api/v1/auth/login`;

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Simulated backend: refresh returns "fresh"; other endpoints accept only "Bearer fresh". */
function fakeBackend({ refreshSucceeds = true } = {}) {
  const calls = { refresh: 0, api: 0 };
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const request = input instanceof Request ? input : new Request(input, init);
    const path = new URL(request.url).pathname;

    if (path === "/api/v1/auth/refresh") {
      calls.refresh += 1;
      return Promise.resolve(
        refreshSucceeds
          ? json(200, { access_token: "fresh", token_type: "bearer", expires_in: 900 })
          : json(401, { detail: "Session expired. Please log in again." }),
      );
    }

    calls.api += 1;
    const authorized = request.headers.get("Authorization") === "Bearer fresh";
    return Promise.resolve(authorized ? json(200, []) : json(401, { detail: "Not authenticated" }));
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, fetchMock };
}

describe("authFetch", () => {
  beforeEach(() => {
    tokenStore.clear();
  });

  it("attaches the access token as a bearer header", async () => {
    tokenStore.set("fresh");
    const { calls } = fakeBackend();

    const response = await authFetch(new Request(ORGS_URL));

    expect(response.status).toBe(200);
    expect(calls.refresh).toBe(0);
  });

  it("refreshes an expired token once and retries the request", async () => {
    tokenStore.set("expired");
    const { calls } = fakeBackend();

    const response = await authFetch(new Request(ORGS_URL));

    expect(response.status).toBe(200);
    expect(calls.refresh).toBe(1);
    expect(tokenStore.get()).toBe("fresh");
  });

  it("shares a single refresh between concurrent requests", async () => {
    tokenStore.set("expired");
    const { calls } = fakeBackend();

    const responses = await Promise.all(
      [1, 2, 3, 4, 5].map(() => authFetch(new Request(ORGS_URL))),
    );

    expect(responses.map((response) => response.status)).toEqual([200, 200, 200, 200, 200]);
    expect(calls.refresh).toBe(1);
  });

  it("clears the token when the session has ended", async () => {
    tokenStore.set("expired");
    const { calls } = fakeBackend({ refreshSucceeds: false });

    const response = await authFetch(new Request(ORGS_URL));

    expect(response.status).toBe(401);
    expect(calls.refresh).toBe(1);
    expect(tokenStore.get()).toBeNull();
  });

  it("never refreshes on a failed login", async () => {
    const { calls } = fakeBackend();

    const response = await authFetch(new Request(LOGIN_URL, { method: "POST" }));

    expect(response.status).toBe(401);
    expect(calls.refresh).toBe(0);
  });
});
