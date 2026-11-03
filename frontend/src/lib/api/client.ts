import createClient from "openapi-fetch";

import { API_ORIGIN } from "../config";
import { authFetch } from "./auth-fetch";
import type { paths } from "./schema";

/**
 * The typed API client. Paths, parameters, request bodies and responses are
 * checked against the backend's OpenAPI schema at compile time.
 */
export const api = createClient<paths>({
  baseUrl: API_ORIGIN,
  fetch: authFetch,
  credentials: "include",
});
