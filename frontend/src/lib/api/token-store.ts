// The access token lives only in memory, never in localStorage or sessionStorage,
// so injected scripts cannot harvest a stored token. A page reload clears it;
// the HttpOnly refresh cookie then restores the session via /auth/refresh.

type Listener = (token: string | null) => void;

let accessToken: string | null = null;
const listeners = new Set<Listener>();

function notify(): void {
  for (const listener of listeners) listener(accessToken);
}

export const tokenStore = {
  get(): string | null {
    return accessToken;
  },

  set(token: string): void {
    accessToken = token;
    notify();
  },

  clear(): void {
    if (accessToken === null) return;
    accessToken = null;
    notify();
  },

  /** Be told whenever the token changes (used by the auth state in step 3.5). */
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
};
