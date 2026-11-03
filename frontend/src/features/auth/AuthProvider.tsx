import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { api } from "../../lib/api/client";
import { errorMessage, fieldErrors } from "../../lib/api/errors";
import { refreshAccessToken } from "../../lib/api/refresh";
import { tokenStore } from "../../lib/api/token-store";
import {
  AuthContext,
  AuthError,
  type AuthContextValue,
  type AuthStatus,
  type RegisterInput,
  type User,
} from "./auth-context";

type AuthState = { status: AuthStatus; user: User | null };

const ANONYMOUS: AuthState = { status: "anonymous", user: null };

async function fetchCurrentUser(): Promise<User | null> {
  const { data } = await api.GET("/api/v1/auth/me");
  return data ?? null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>({ status: "loading", user: null });

  // Ending a session also wipes cached server data, so the next person to use this
  // browser can never see the previous user's organizations, even briefly.
  const becomeAnonymous = useCallback(() => {
    queryClient.clear();
    setState(ANONYMOUS);
  }, [queryClient]);

  // On first load, try to restore the session from the HttpOnly refresh cookie.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const token = await refreshAccessToken();
      const user = token === null ? null : await fetchCurrentUser();
      if (!cancelled) setState(user ? { status: "authenticated", user } : ANONYMOUS);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // If the session ends anywhere (failed refresh, logout in this tab), become anonymous.
  useEffect(
    () =>
      tokenStore.subscribe((token) => {
        if (token === null) becomeAnonymous();
      }),
    [becomeAnonymous],
  );

  const login = useCallback(async (email: string, password: string) => {
    const { data, error } = await api.POST("/api/v1/auth/login", { body: { email, password } });
    if (data === undefined) {
      throw new AuthError(errorMessage(error, "Unable to sign in."), fieldErrors(error));
    }
    tokenStore.set(data.access_token);
    const user = await fetchCurrentUser();
    if (user === null) {
      throw new AuthError("Signed in, but your profile could not be loaded. Please try again.");
    }
    setState({ status: "authenticated", user });
  }, []);

  const register = useCallback(
    async ({ fullName, email, password }: RegisterInput) => {
      const { data, error } = await api.POST("/api/v1/auth/register", {
        body: { full_name: fullName, email, password },
      });
      if (data === undefined) {
        throw new AuthError(
          errorMessage(error, "Unable to create your account."),
          fieldErrors(error),
        );
      }
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    try {
      await api.POST("/api/v1/auth/logout");
    } finally {
      // Even if the network call fails, this browser forgets the session.
      tokenStore.clear();
      becomeAnonymous();
    }
  }, [becomeAnonymous]);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, login, register, logout }),
    [state, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
