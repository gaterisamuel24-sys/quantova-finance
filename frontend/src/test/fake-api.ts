import { vi } from "vitest";

export type FetchHandler = (request: Request) => Response | Promise<Response>;

export function json(status: number, body?: unknown): Response {
  if (body === undefined) return new Response(null, { status });
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Replace global fetch with a simulated backend. Returns the mock to inspect calls. */
export function stubFetch(handler: FetchHandler) {
  const mock = vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
    Promise.resolve(handler(input instanceof Request ? input : new Request(input, init))),
  );
  vi.stubGlobal("fetch", mock);
  return mock;
}
