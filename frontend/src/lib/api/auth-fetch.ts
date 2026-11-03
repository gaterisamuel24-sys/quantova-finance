import { refreshAccessToken } from "./refresh";
import { tokenStore } from "./token-store";

// Endpoints that must never trigger an automatic refresh-and-retry.
const NO_RETRY_PATHS = new Set([
  "/api/v1/auth/login",
  "/api/v1/auth/register",
  "/api/v1/auth/refresh",
  "/api/v1/auth/logout",
]);

function withAccessToken(request: Request): Request {
  const token = tokenStore.get();
  if (token === null) return request;
  const headers = new Headers(request.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return new Request(request, { headers });
}

/**
 * fetch() with authentication: attaches the access token, and on 401 refreshes it
 * once and retries the original request.
 */
export async function authFetch(request: Request): Promise<Response> {
  // A request body can be read only once, so keep an untouched copy for the retry.
  const retryCopy = request.clone();

  const response = await fetch(withAccessToken(request));
  if (response.status !== 401 || NO_RETRY_PATHS.has(new URL(request.url).pathname)) {
    return response;
  }

  const newToken = await refreshAccessToken();
  if (newToken === null) return response;
  return fetch(withAccessToken(retryCopy));
}
