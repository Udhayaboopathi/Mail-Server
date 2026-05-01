"use client";

import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import type { Whitelabel } from "@/types";

export type WhitelabelContextValue = {
  whitelabel: Whitelabel;
  setWhitelabel: (value: Whitelabel) => void;
};

const WhitelabelContext = createContext<WhitelabelContextValue | undefined>(
  undefined,
);

const STORAGE_KEY = "mail-whitelabel";

export function WhitelabelProvider({ children }: { children: ReactNode }) {
  const [whitelabel, setWhitelabel] = useState<Whitelabel>({});

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setWhitelabel(JSON.parse(stored) as Whitelabel);
      } catch {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  useEffect(() => {
    const color = whitelabel.primary_color ?? "#6366f1";
    document.documentElement.style.setProperty("--brand-primary", color);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(whitelabel));
  }, [whitelabel]);

  const value = useMemo(() => ({ whitelabel, setWhitelabel }), [whitelabel]);

  return (
    <WhitelabelContext.Provider value={value}>
      {children}
    </WhitelabelContext.Provider>
  );
}

export function useWhitelabel(): WhitelabelContextValue {
  const context = useContext(WhitelabelContext);
  if (!context) {
    throw new Error("useWhitelabel must be used within WhitelabelProvider");
  }
  return context;
}
