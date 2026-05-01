import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { AuthTokens, User } from "@/types";

export type AuthState = {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  setSession: (tokens: AuthTokens, user?: User | null) => void;
  clearSession: () => void;
};

type AuthSet = (state: Partial<AuthState>) => void;

const authStoreCreator = (set: AuthSet): AuthState => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  setSession: (tokens, user = null) =>
    set({
      user,
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
    }),
  clearSession: () =>
    set({ user: null, accessToken: null, refreshToken: null }),
});

export const useAuthStore = create<AuthState>()(
  persist(authStoreCreator, { name: "email-system-auth" }),
);

export function getAuthSnapshot() {
  const state = useAuthStore.getState();
  return {
    accessToken: state.accessToken,
    refreshToken: state.refreshToken,
    user: state.user,
  };
}
