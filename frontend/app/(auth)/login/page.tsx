"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { type AuthState, useAuthStore } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const setSession = useAuthStore((state: AuthState) => state.setSession);
  const [email, setEmail] = useState("");
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
    <div className="flex min-h-screen items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-3xl border border-black/10 bg-white/90 p-8 shadow-panel backdrop-blur"
      >
        <div className="mb-8 space-y-3">
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-ember">
            Self-hosted mail
          </p>
          <h1 className="text-3xl font-semibold text-ink">Sign in</h1>
          <p className="text-sm text-ink/70">
            Access your mailbox and admin tools.
          </p>
        </div>
        <div className="space-y-4">
          <input
            className="w-full rounded-2xl border border-black/10 bg-paper px-4 py-3"
            placeholder="Email"
            value={email}
            onChange={(event: { target: { value: string } }) =>
              setEmail(event.target.value)
            }
          />
          <input
            className="w-full rounded-2xl border border-black/10 bg-paper px-4 py-3"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(event: { target: { value: string } }) =>
              setPassword(event.target.value)
            }
          />
          {error ? <p className="text-sm text-ember">{error}</p> : null}
          <button
            disabled={loading}
            className="w-full rounded-2xl bg-ink px-4 py-3 font-medium text-paper transition hover:bg-ink/90 disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </div>
      </form>
    </div>
  );
}
