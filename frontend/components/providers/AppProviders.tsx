"use client";

import { ReactNode, useEffect } from "react";

import { QueryProvider } from "@/components/providers/QueryProvider";
import { WhitelabelProvider } from "@/components/providers/WhitelabelProvider";

const THEME_KEY = "mail-theme";

function applyTheme(value: "light" | "dark") {
  document.documentElement.classList.toggle("dark", value === "dark");
  window.localStorage.setItem(THEME_KEY, value);
}

export function AppProviders({ children }: { children: ReactNode }) {
  useEffect(() => {
    const stored = window.localStorage.getItem(THEME_KEY) as
      | "light"
      | "dark"
      | null;
    if (stored) {
      applyTheme(stored);
    } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      applyTheme("dark");
    } else {
      applyTheme("light");
    }

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    }
  }, []);

  return (
    <WhitelabelProvider>
      <QueryProvider>{children}</QueryProvider>
    </WhitelabelProvider>
  );
}

export function setTheme(value: "light" | "dark") {
  applyTheme(value);
}
