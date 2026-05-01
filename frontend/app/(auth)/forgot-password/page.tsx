"use client";

import { type FormEvent, useState } from "react";
import Link from "next/link";

import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setStatus(null);
    setLoading(true);
    try {
      await api.passwordReset.request(email);
      setStatus("Check your inbox for a reset link.");
      setEmail("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to send reset link.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper p-6 dark:bg-gray-950">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-3xl border border-black/10 bg-white/90 p-8 shadow-panel backdrop-blur dark:border-gray-700 dark:bg-gray-900/90"
      >
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-ink dark:text-gray-100">
            Reset your password
          </h1>
          <p className="mt-2 text-sm text-ink/70 dark:text-gray-400">
            Enter your email to receive a reset link.
          </p>
        </div>
        <div className="space-y-4">
          <input
            className="w-full rounded-2xl border border-black/10 bg-paper px-4 py-3 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            placeholder="Email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
          />
          {status ? <p className="text-sm text-emerald-600">{status}</p> : null}
          {error ? <p className="text-sm text-ember">{error}</p> : null}
          <button
            disabled={loading}
            className="w-full rounded-2xl bg-ink px-4 py-3 font-medium text-paper transition hover:bg-ink/90 disabled:opacity-60"
          >
            {loading ? "Sending..." : "Send reset link"}
          </button>
        </div>
        <div className="mt-6 text-sm text-ink/70 dark:text-gray-400">
          Remembered your password?{" "}
          <Link href="/login" className="text-ember">
            Back to sign in
          </Link>
        </div>
      </form>
    </div>
  );
}
