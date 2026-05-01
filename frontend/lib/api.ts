import type {
  AuthTokens,
  DNSRecords,
  Domain,
  FolderSummary,
  MailMessage,
  MailSendRequest,
  MailSummary,
  Mailbox,
  Stats,
  User,
} from "@/types";
import { getAuthSnapshot, useAuthStore } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as T;
}

async function refreshSession(): Promise<AuthTokens | null> {
  const refreshToken = getAuthSnapshot().refreshToken;
  if (!refreshToken) {
    return null;
  }
  const response = await fetch("/api/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) {
    useAuthStore.getState().clearSession();
    return null;
  }
  const tokens = (await response.json()) as AuthTokens;
  useAuthStore.getState().setSession(tokens);
  return tokens;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const { accessToken } = getAuthSnapshot();
  const headers = new Headers(init.headers ?? {});
  headers.set("Content-Type", "application/json");
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (response.status === 401) {
    const refreshed = await refreshSession();
    if (refreshed) {
      headers.set("Authorization", `Bearer ${refreshed.access_token}`);
      const retry = await fetch(`${API_BASE}${path}`, {
        ...init,
        headers,
        credentials: "include",
      });
      return parseJsonResponse<T>(retry);
    }
  }
  return parseJsonResponse<T>(response);
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      apiFetch<AuthTokens>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    refresh: (refresh_token: string) =>
      apiFetch<AuthTokens>("/api/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token }),
      }),
    logout: (refresh_token: string) =>
      apiFetch<{ status: string }>("/api/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token }),
      }),
  },
  mail: {
    folders: () => apiFetch<FolderSummary>("/api/mail/folders"),
    list: (folder: string, page = 1, limit = 50) =>
      apiFetch<MailSummary[]>(
        `/api/mail/${encodeURIComponent(folder)}?page=${page}&limit=${limit}`,
      ),
    get: (folder: string, uid: number) =>
      apiFetch<MailMessage>(`/api/mail/${encodeURIComponent(folder)}/${uid}`),
    send: (payload: MailSendRequest) =>
      apiFetch<{ status: string }>("/api/mail/send", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    delete: (folder: string, uid: number) =>
      apiFetch<{ status: string }>(
        `/api/mail/${encodeURIComponent(folder)}/${uid}`,
        { method: "DELETE" },
      ),
    flags: (folder: string, uid: number, flags: Record<string, boolean>) =>
      apiFetch<{ status: string }>(
        `/api/mail/${encodeURIComponent(folder)}/${uid}/flags`,
        { method: "PATCH", body: JSON.stringify(flags) },
      ),
    move: (folder: string, uid: number, destination: string) =>
      apiFetch<{ status: string }>(
        `/api/mail/${encodeURIComponent(folder)}/${uid}/move`,
        { method: "POST", body: JSON.stringify({ folder: destination }) },
      ),
    search: (q: string) =>
      apiFetch<{ results: MailSummary[] }>(
        `/api/mail/search?q=${encodeURIComponent(q)}`,
      ),
  },
  domains: {
    list: () => apiFetch<Domain[]>("/api/domains"),
    create: (name: string) =>
      apiFetch<Domain>("/api/domains", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    remove: (id: string) =>
      apiFetch<{ status: string }>(`/api/domains/${id}`, { method: "DELETE" }),
    dnsRecords: (id: string) =>
      apiFetch<DNSRecords>(`/api/domains/${id}/dns-records`),
  },
  mailboxes: {
    list: () => apiFetch<Mailbox[]>("/api/mailboxes"),
    create: (payload: {
      user_id: string;
      domain_id: string;
      local_part: string;
      password: string;
      quota_mb: number;
    }) =>
      apiFetch<Mailbox>("/api/mailboxes", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    update: (
      id: string,
      payload: Partial<{
        password: string;
        quota_mb: number;
        is_active: boolean;
      }>,
    ) =>
      apiFetch<Mailbox>(`/api/mailboxes/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) =>
      apiFetch<{ status: string }>(`/api/mailboxes/${id}`, {
        method: "DELETE",
      }),
  },
  users: {
    list: () => apiFetch<User[]>("/api/users"),
    create: (payload: {
      email: string;
      password: string;
      is_admin?: boolean;
      is_active?: boolean;
    }) =>
      apiFetch<User>("/api/users", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    update: (
      id: string,
      payload: Partial<{
        email: string;
        password: string;
        is_admin: boolean;
        is_active: boolean;
      }>,
    ) =>
      apiFetch<User>(`/api/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) =>
      apiFetch<{ status: string }>(`/api/users/${id}`, { method: "DELETE" }),
  },
  admin: {
    stats: () => apiFetch<Stats>("/api/admin/stats"),
    logs: (page = 1, limit = 50) =>
      apiFetch<{ items: unknown[]; page: number; limit: number }>(
        `/api/admin/logs?page=${page}&limit=${limit}`,
      ),
  },
};
