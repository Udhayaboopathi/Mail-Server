"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { type AuthState, useAuthStore } from "@/lib/auth";
import { setTheme } from "@/components/providers/AppProviders";

export function Topbar({ onCompose }: { onCompose?: () => void }) {
  const router = useRouter();
  const user = useAuthStore((state: AuthState) => state.user);
  const clearSession = useAuthStore((state: AuthState) => state.clearSession);
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem("mail-theme");
    if (stored) {
      setIsDark(stored === "dark");
    } else {
      setIsDark(window.matchMedia("(prefers-color-scheme: dark)").matches);
    }
  }, []);

  async function handleLogout() {
    const refreshToken = useAuthStore.getState().refreshToken;
    if (refreshToken) {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    }
    clearSession();
    router.push("/login");
  }

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    setTheme(next ? "dark" : "light");
  };

  return (
    <header className="flex flex-col gap-4 border-b border-black/10 bg-white/70 px-4 py-4 backdrop-blur lg:flex-row lg:items-center lg:justify-between lg:px-8 dark:border-gray-700 dark:bg-gray-900/70">
      <div className="flex items-center gap-3">
        <div className="hidden h-11 w-11 items-center justify-center rounded-2xl bg-ink text-paper lg:flex">
          ✉
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-ember">
            Workspace
          </p>
          <h1 className="text-xl font-semibold text-ink dark:text-gray-100">
            {user?.email ?? "Mailbox"}
          </h1>
        </div>
      </div>
      <div className="flex flex-1 items-center gap-3 lg:mx-8 lg:max-w-2xl">
        <Input placeholder="Search mail" />
        <Button
          className="shrink-0 bg-ember hover:bg-ember/90"
          onClick={onCompose}
        >
          Compose
        </Button>
      </div>
      <div className="flex items-center gap-3">
        <Button
          className="bg-sand text-ink hover:bg-sand/80 dark:bg-gray-800 dark:text-gray-100"
          onClick={toggleTheme}
          type="button"
        >
          {isDark ? "Light" : "Dark"}
        </Button>
        <Avatar name={user?.email ?? "User"} />
        <Button
          className="bg-sand text-ink hover:bg-sand/80 dark:bg-gray-800 dark:text-gray-100"
          onClick={handleLogout}
        >
          Logout
        </Button>
      </div>
    </header>
  );
}
