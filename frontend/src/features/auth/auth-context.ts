import { createContext, useContext } from "react";

import type { components } from "../../lib/api/schema";

export type User = components["schemas"]["UserResponse"];
export type AuthStatus = "loading" | "authenticated" | "anonymous";

export type RegisterInput = { fullName: string; email: string; password: string };

export type AuthContextValue = {
  status: AuthStatus;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => Promise<void>;
};

/** A failure the person can act on, with optional per-field messages. */
export class AuthError extends Error {
  readonly fieldErrors: Record<string, string>;

  constructor(message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = "AuthError";
    this.fieldErrors = fieldErrors;
  }
}

export function describeAuthFailure(error: unknown): string {
  return error instanceof AuthError
    ? error.message
    : "We couldn't reach the server. Check your connection and try again.";
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
