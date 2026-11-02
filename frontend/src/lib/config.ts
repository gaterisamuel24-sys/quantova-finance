// Central place for runtime configuration read from VITE_* variables.

/** API base URL without a trailing slash. Empty string means "same origin". */
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(
  /\/+$/,
  "",
);

/** Build a full API URL from a path such as "/api/v1/health". */
export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}
