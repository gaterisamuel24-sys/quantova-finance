import { API_ORIGIN } from "../config";
import type { components } from "./schema";
import { tokenStore } from "./token-store";

type TokenResponse = components["schemas"]["TokenResponse"];

const REFRESH_URL = `${API_ORIGIN}/api/v1/auth/refresh`;
const CROSS_TAB_LOCK = "quantova-token-refresh";

let inFlight: Promise<string | null> | null = null;

/**
 * Get a new access token using the HttpOnly refresh cookie.
 *
 * Single-flight: concurrent callers share one request. Across browser tabs, the
 * Web Locks API makes refreshes take turns, so two tabs never present the same
 * refresh token at once (which the server would treat as token theft).
 * Returns the new token, or null if the session has ended.
 */
export function refreshAccessToken(): Promise<string | null> {
  inFlight ??= withCrossTabLock(requestNewAccessToken).finally(() => {
    inFlight = null;
  });
  return inFlight;
}

async function requestNewAccessToken(): Promise<string | null> {
  let response: Response;
  try {
    response = await fetch(REFRESH_URL, { method: "POST", credentials: "include" });
  } catch {
    // Network failure: leave the session as it is; the caller sees its original error.
    return null;
  }

  if (!response.ok) {
    tokenStore.clear();
    return null;
  }
  const body = (await response.json()) as TokenResponse;
  tokenStore.set(body.access_token);
  return body.access_token;
}

function withCrossTabLock<T>(task: () => Promise<T>): Promise<T> {
  if (typeof navigator !== "undefined" && "locks" in navigator) {
    return navigator.locks.request(CROSS_TAB_LOCK, task);
  }
  return task();
}
