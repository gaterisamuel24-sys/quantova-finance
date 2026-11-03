// The Content Security Policy for the built app: which sources the browser may load.
//
// It is strict: scripts, styles and fonts only from our own origin, no inline scripts, no
// eval, no plugins, no framing. If an attacker ever got text onto a page (for example a
// malicious transaction description), the browser would still refuse to run it.
// Used by vite.config.ts; pure so it can be unit-tested.

/** The origin (scheme://host[:port]) of a URL, or an error for anything else. */
export function originOf(url: string): string {
  const parsed = new URL(url);
  if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
    throw new Error(`Not an http(s) URL: ${url}`);
  }
  return parsed.origin;
}

/**
 * Build the policy. `apiBaseUrl` is VITE_API_BASE_URL: empty when the API is served from
 * the same origin as the app, otherwise the API's own address, which fetch() must reach.
 */
export function buildContentSecurityPolicy(apiBaseUrl = ""): string {
  const connect = ["'self'"];
  if (apiBaseUrl) connect.push(originOf(apiBaseUrl));

  const directives: Record<string, string[]> = {
    "default-src": ["'self'"],
    "script-src": ["'self'"],
    "style-src": ["'self'"],
    "font-src": ["'self'"],
    // data: and blob: for small generated images and downloaded report files.
    "img-src": ["'self'", "data:", "blob:"],
    "connect-src": connect,
    "object-src": ["'none'"],
    "frame-src": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
  };
  return Object.entries(directives)
    .map(([name, values]) => [name, ...values].join(" "))
    .join("; ");
}
