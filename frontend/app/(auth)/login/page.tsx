"use client";

import { type ChangeEvent, type FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { type AuthState, useAuthStore } from "@/lib/auth";
import { api } from "@/lib/api";
import { useWhitelabel } from "@/components/providers/WhitelabelProvider";

export default function LoginPage() {
  const router = useRouter();
  const { whitelabel, setWhitelabel } = useWhitelabel();
  const setSession = useAuthStore((state: AuthState) => state.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const domain = params.get("domain");
    if (!domain) {
      return;
    }
    fetch(`/api/admin/whitelabel?domain=${encodeURIComponent(domain)}`)
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data) {
          setWhitelabel(data);
        }
      })
      .catch(() => undefined);
  }, [setWhitelabel]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        throw new Error("Invalid credentials");
      }
      const tokens = await response.json();
      setSession(tokens);
      router.push("/mail/inbox");
    } catch (loginError) {
      setError(
        loginError instanceof Error ? loginError.message : "Login failed",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper p-6 dark:bg-gray-950">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-3xl border border-black/10 bg-white/90 p-8 shadow-panel backdrop-blur dark:border-gray-700 dark:bg-gray-900/90"
      >
        <div className="mb-8 space-y-3">
          {whitelabel.logo_url ? (
            <img
              src={whitelabel.logo_url}
              alt={whitelabel.company_name ?? "Logo"}
              className="h-10"
            />
          ) : (
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-ember">
              Self-hosted mail
            </p>
          )}
          <h1 className="text-3xl font-semibold text-ink dark:text-gray-100">
            {whitelabel.company_name ?? "Sign in"}
          </h1>
          <p className="text-sm text-ink/70 dark:text-gray-400">
            Access your mailbox and admin tools.
          </p>
        </div>
        <div className="space-y-4">
          <input
            className="w-full rounded-2xl border border-black/10 bg-paper px-4 py-3 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            placeholder="Email"
            value={email}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setEmail(event.target.value)
            }
          />
          <input
            className="w-full rounded-2xl border border-black/10 bg-paper px-4 py-3 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setPassword(event.target.value)
            }
          />
          {error ? <p className="text-sm text-ember">{error}</p> : null}
          <button
            disabled={loading}
            className="w-full rounded-2xl bg-ink px-4 py-3 font-medium text-paper transition hover:bg-ink/90 disabled:opacity-60"
            style={{ backgroundColor: "var(--brand-primary)" }}
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
          <div className="text-right">
            <Link href="/forgot-password" className="text-sm text-ember">
              Forgot password?
            </Link>
          </div>
        </div>
      </form>
    </div>
  );
}
