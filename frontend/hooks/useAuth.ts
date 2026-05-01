import { useMemo } from "react";

import { type AuthState, useAuthStore } from "@/lib/auth";

export function useAuth() {
  const user = useAuthStore((state: AuthState) => state.user);
  const accessToken = useAuthStore((state: AuthState) => state.accessToken);
  const refreshToken = useAuthStore((state: AuthState) => state.refreshToken);
  const clearSession = useAuthStore((state: AuthState) => state.clearSession);
  const setSession = useAuthStore((state: AuthState) => state.setSession);

  return useMemo(
    () => ({
      user,
      accessToken,
      refreshToken,
      clearSession,
      setSession,
      isAuthenticated: Boolean(accessToken),
    }),
    [user, accessToken, refreshToken, clearSession, setSession],
  );
}
