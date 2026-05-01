"use client";

import { type FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setToken(params.get("token") ?? "");
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setStatus(null);
    if (!token) {
      setError("Reset token is missing.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await api.passwordReset.confirm(token, password);
      setStatus("Password updated. Redirecting to login...");
      setTimeout(() => router.push("/login"), 1200);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to reset password.",
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
            Create a new password
          </h1>
          <p className="mt-2 text-sm text-ink/70 dark:text-gray-400">
            Choose a strong password for your mailbox.
          </p>
        </div>
        <div className="space-y-4">
          <input
            className="w-full rounded-2xl border border-black/10 bg-paper px-4 py-3 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            placeholder="New password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          <input
            className="w-full rounded-2xl border border-black/10 bg-paper px-4 py-3 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            placeholder="Confirm password"
            type="password"
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            required
          />
          {status ? <p className="text-sm text-emerald-600">{status}</p> : null}
          {error ? <p className="text-sm text-ember">{error}</p> : null}
          <button
            disabled={loading}
            className="w-full rounded-2xl bg-ink px-4 py-3 font-medium text-paper transition hover:bg-ink/90 disabled:opacity-60"
          >
            {loading ? "Saving..." : "Update password"}
          </button>
        </div>
        <div className="mt-6 text-sm text-ink/70 dark:text-gray-400">
          <Link href="/login" className="text-ember">
            Back to sign in
          </Link>
        </div>
      </form>
    </div>
  );
}
