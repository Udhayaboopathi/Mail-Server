"use client";

import { type FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { type AuthState, useAuthStore } from "@/lib/auth";

export default function SuperAdminLoginPage() {
  const router = useRouter();
  const setSession = useAuthStore((state: AuthState) => state.setSession);
  const clearSession = useAuthStore((state: AuthState) => state.clearSession);

  const [email, setEmail] = useState("admin@yourdomain.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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

      // Validate this account can access admin APIs before redirecting.
      await api.admin.stats();
      router.push("/admin");
    } catch (loginError) {
      clearSession();
      setError(
        loginError instanceof Error
          ? loginError.message
          : "Superadmin login failed",
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
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-ember">
            Admin Console
          </p>
          <h1 className="text-3xl font-semibold text-ink dark:text-gray-100">
            Superadmin sign in
          </h1>
          <p className="text-sm text-ink/70 dark:text-gray-400">
            Use a superadmin account to access the admin dashboard.
          </p>
        </div>

        <div className="space-y-4">
          <input
            className="w-full rounded-2xl border border-black/10 bg-paper px-4 py-3 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            placeholder="Superadmin email"
            value={email}
            onChange={(event) => setEmail(event.currentTarget.value)}
            autoComplete="email"
          />

          <input
            className="w-full rounded-2xl border border-black/10 bg-paper px-4 py-3 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.currentTarget.value)}
            autoComplete="current-password"
          />

          {error ? <p className="text-sm text-ember">{error}</p> : null}

          <button
            disabled={loading}
            className="w-full rounded-2xl bg-ink px-4 py-3 font-medium text-paper transition hover:bg-ink/90 disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Sign in to Admin"}
          </button>

          <div className="text-sm text-ink/70 dark:text-gray-400">
            Need normal mailbox access?{" "}
            <Link href="/login" className="text-ember">
              Go to user login
            </Link>
          </div>
        </div>
      </form>
    </div>
  );
}
