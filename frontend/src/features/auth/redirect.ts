const DEFAULT_DESTINATION = "/app";

/**
 * Where to go after signing in. Only same-app paths are allowed: "/app/reports" is fine,
 * but "https://evil.example" or "//evil.example" are not (open-redirect protection).
 */
export function safeRedirect(state: unknown): string {
  const from =
    typeof state === "object" && state !== null ? (state as { from?: unknown }).from : null;
  if (typeof from === "string" && from.startsWith("/") && !from.startsWith("//")) return from;
  return DEFAULT_DESTINATION;
}
