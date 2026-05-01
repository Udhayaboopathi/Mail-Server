import type {
  AuthTokens,
  ApiKey,
  ApiKeyCreated,
  AiPriorityInboxResponse,
  AiSmartReplyResponse,
  AiSummaryResponse,
  CalendarEvent,
  Campaign,
  CampaignAnalytics,
  DelegationRecord,
  DNSRecords,
  Domain,
  EdiscoveryExport,
  FolderSummary,
  Label,
  LoginActivityItem,
  MailMessage,
  MailSendRequest,
  MailSummary,
  Mailbox,
  NoteItem,
  PgpKeyResponse,
  SharedMailbox,
  Stats,
  TaskItem,
  Template,
  ThreadMessage,
  ThreadSummary,
  TotpSetupResponse,
  User,
  Whitelabel,
  Webhook,
  Rule,
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
  totp: {
    setup: () =>
      apiFetch<TotpSetupResponse>("/api/auth/totp/setup", { method: "POST" }),
    enable: (code: string) =>
      apiFetch<{ enabled: boolean }>("/api/auth/totp/enable", {
        method: "POST",
        body: JSON.stringify({ code }),
      }),
    verify: (code: string) =>
      apiFetch<AuthTokens>("/api/auth/totp/verify", {
        method: "POST",
        body: JSON.stringify({ code }),
      }),
    disable: (password: string) =>
      apiFetch<{ disabled: boolean }>("/api/auth/totp/disable", {
        method: "POST",
        body: JSON.stringify({ password }),
      }),
    loginActivity: () =>
      apiFetch<LoginActivityItem[]>("/api/auth/login-activity"),
  },
  passwordReset: {
    request: (email: string) =>
      apiFetch<{ status: string }>("/api/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      }),
    confirm: (token: string, newPassword: string) =>
      apiFetch<{ status: string }>("/api/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ token, new_password: newPassword }),
      }),
  },
  pgp: {
    generate: (passphrase: string) =>
      apiFetch<PgpKeyResponse>("/api/pgp/generate", {
        method: "POST",
        body: JSON.stringify({ passphrase }),
      }),
    getPublicKey: () => apiFetch<PgpKeyResponse>("/api/pgp/public-key"),
    lookupPublicKey: (email: string) =>
      apiFetch<PgpKeyResponse>(
        `/api/pgp/public-key/${encodeURIComponent(email)}`,
      ),
    deleteKey: () =>
      apiFetch<{ status: string }>("/api/pgp/key", { method: "DELETE" }),
  },
  threads: {
    list: (folder: string, page = 1, limit = 50) =>
      apiFetch<ThreadSummary[]>(
        `/api/mail/threads/${encodeURIComponent(folder)}?page=${page}&limit=${limit}`,
      ),
    messages: (threadId: string) =>
      apiFetch<ThreadMessage[]>(`/api/mail/threads/${threadId}/messages`),
  },
  labels: {
    list: () => apiFetch<Label[]>("/api/labels"),
    create: (name: string, color: string) =>
      apiFetch<Label>("/api/labels", {
        method: "POST",
        body: JSON.stringify({ name, color }),
      }),
    update: (id: string, payload: Partial<{ name: string; color: string }>) =>
      apiFetch<Label>(`/api/labels/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) =>
      apiFetch<{ status: string }>(`/api/labels/${id}`, { method: "DELETE" }),
    apply: (labelId: string, emailUid: string) =>
      apiFetch<{ status: string }>(`/api/labels/${labelId}/apply/${emailUid}`, {
        method: "POST",
      }),
    removeFromEmail: (labelId: string, emailUid: string) =>
      apiFetch<{ status: string }>(`/api/labels/${labelId}/apply/${emailUid}`, {
        method: "DELETE",
      }),
  },
  rules: {
    list: () => apiFetch<Rule[]>("/api/rules"),
    create: (payload: {
      name: string;
      match_type: string;
      conditions: { field: string; op: string; value?: string | null }[];
      actions: { type: string; value?: string | null }[];
      priority: number;
    }) =>
      apiFetch<Rule>("/api/rules", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    update: (id: string, payload: Partial<Rule>) =>
      apiFetch<Rule>(`/api/rules/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) =>
      apiFetch<{ status: string }>(`/api/rules/${id}`, { method: "DELETE" }),
    test: (id: string) =>
      apiFetch<
        {
          uid: string;
          subject: string;
          would_apply: boolean;
          actions_that_would_run: string[];
        }[]
      >(`/api/rules/${id}/test`, { method: "POST" }),
  },
  templates: {
    list: () => apiFetch<Template[]>("/api/templates"),
    create: (payload: {
      name: string;
      subject: string;
      body_text?: string | null;
      body_html?: string | null;
    }) =>
      apiFetch<Template>("/api/templates", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    update: (id: string, payload: Partial<Template>) =>
      apiFetch<Template>(`/api/templates/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) =>
      apiFetch<{ status: string }>(`/api/templates/${id}`, {
        method: "DELETE",
      }),
    use: (id: string) => apiFetch<Template>(`/api/templates/${id}/use`),
  },
  ai: {
    summarize: (payload: {
      thread_id?: string;
      messages?: {
        from: string;
        subject: string;
        body: string;
        date?: string;
      }[];
    }) =>
      apiFetch<AiSummaryResponse>("/api/ai/summarize", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    smartReply: (threadId: string) =>
      apiFetch<AiSmartReplyResponse>("/api/ai/smart-reply", {
        method: "POST",
        body: JSON.stringify({ thread_id: threadId }),
      }),
    priorityInbox: () =>
      apiFetch<AiPriorityInboxResponse>("/api/ai/priority-inbox"),
    suggestLabels: (emailUid: number) =>
      apiFetch<{ suggestions: string[] }>("/api/ai/suggest-labels", {
        method: "POST",
        body: JSON.stringify({ email_uid: emailUid }),
      }),
  },
  calendar: {
    events: (startIso: string, endIso: string) =>
      apiFetch<CalendarEvent[]>(
        `/api/calendar/events?start=${encodeURIComponent(startIso)}&end=${encodeURIComponent(endIso)}`,
      ),
    create: (
      payload: Partial<CalendarEvent> & { uid: string; title: string },
    ) =>
      apiFetch<CalendarEvent>("/api/calendar/events", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    update: (id: string, payload: Partial<CalendarEvent>) =>
      apiFetch<CalendarEvent>(`/api/calendar/events/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) =>
      apiFetch<{ deleted: boolean }>(`/api/calendar/events/${id}`, {
        method: "DELETE",
      }),
    importIcs: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE}/api/calendar/import`, {
        method: "POST",
        body: formData,
      });
      return parseJsonResponse<{ imported: number }>(response);
    },
    exportIcs: async () => {
      const response = await fetch(`${API_BASE}/api/calendar/export`);
      if (!response.ok) {
        throw new Error(await response.text());
      }
      return response.blob();
    },
  },
  tasks: {
    list: (completed?: boolean) =>
      apiFetch<TaskItem[]>(
        completed === undefined
          ? "/api/tasks"
          : `/api/tasks?completed=${completed}`,
      ),
    create: (payload: {
      title: string;
      description?: string | null;
      due_at?: string | null;
      priority: string;
      linked_email_uid?: string | null;
    }) =>
      apiFetch<TaskItem>("/api/tasks", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    update: (id: string, payload: Partial<TaskItem>) =>
      apiFetch<TaskItem>(`/api/tasks/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) =>
      apiFetch<{ status: string }>(`/api/tasks/${id}`, { method: "DELETE" }),
    complete: (id: string) =>
      apiFetch<{ completed: boolean }>(`/api/tasks/${id}/complete`, {
        method: "POST",
      }),
    createFromEmail: (uid: number) =>
      apiFetch<TaskItem>(`/api/tasks/from-email/${uid}`, { method: "POST" }),
  },
  notes: {
    list: () => apiFetch<NoteItem[]>("/api/notes"),
    create: (payload: {
      title?: string | null;
      body: string;
      linked_email_uid?: string | null;
    }) =>
      apiFetch<NoteItem>("/api/notes", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    update: (id: string, payload: Partial<NoteItem>) =>
      apiFetch<NoteItem>(`/api/notes/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) =>
      apiFetch<{ status: string }>(`/api/notes/${id}`, { method: "DELETE" }),
  },
  sharedMailboxes: {
    list: () => apiFetch<SharedMailbox[]>("/api/shared-mailboxes"),
    create: (payload: { local_part: string; display_name: string }) =>
      apiFetch<SharedMailbox>("/api/shared-mailboxes", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    addMember: (id: string, payload: { user_id: string; permission: string }) =>
      apiFetch<{ status: string }>(`/api/shared-mailboxes/${id}/members`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    removeMember: (id: string, userId: string) =>
      apiFetch<{ status: string }>(
        `/api/shared-mailboxes/${id}/members/${userId}`,
        { method: "DELETE" },
      ),
    inbox: (id: string) =>
      apiFetch<MailSummary[]>(`/api/shared-mailboxes/${id}/inbox`),
  },
  delegation: {
    granted: () => apiFetch<DelegationRecord[]>("/api/delegation/granted"),
    received: () => apiFetch<DelegationRecord[]>("/api/delegation/received"),
    grant: (payload: { delegate_email: string; permission: string }) =>
      apiFetch<{ status: string }>("/api/delegation/grant", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    revoke: (id: string) =>
      apiFetch<{ status: string }>(`/api/delegation/revoke/${id}`, {
        method: "DELETE",
      }),
    inbox: (mailboxId: string) =>
      apiFetch<MailSummary[]>(`/api/delegation/mailbox/${mailboxId}/inbox`),
  },
  apiKeys: {
    list: () => apiFetch<ApiKey[]>("/api/keys"),
    create: (payload: {
      name: string;
      scopes: string[];
      rate_limit_per_hour: number;
      expires_at?: string | null;
    }) =>
      apiFetch<ApiKeyCreated>("/api/keys", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) =>
      apiFetch<{ status: string }>(`/api/keys/${id}`, { method: "DELETE" }),
  },
  campaigns: {
    list: () => apiFetch<Campaign[]>("/api/campaigns"),
    create: (payload: {
      name: string;
      subject: string;
      body_html: string;
      body_text?: string | null;
      from_name?: string | null;
      recipients: {
        email: string;
        name?: string | null;
        vars?: Record<string, string> | null;
      }[];
      scheduled_at?: string | null;
    }) =>
      apiFetch<Campaign>("/api/campaigns", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    update: (id: string, payload: Partial<Campaign>) =>
      apiFetch<Campaign>(`/api/campaigns/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) =>
      apiFetch<{ status: string }>(`/api/campaigns/${id}`, {
        method: "DELETE",
      }),
    send: (id: string) =>
      apiFetch<{ queued: boolean }>(`/api/campaigns/${id}/send`, {
        method: "POST",
      }),
    schedule: (id: string, scheduled_at: string) =>
      apiFetch<{ scheduled: boolean }>(`/api/campaigns/${id}/schedule`, {
        method: "POST",
        body: JSON.stringify({ scheduled_at }),
      }),
    analytics: (id: string) =>
      apiFetch<CampaignAnalytics>(`/api/campaigns/${id}/analytics`),
  },
  webhooks: {
    list: () => apiFetch<Webhook[]>("/api/webhooks"),
    create: (payload: { url: string; secret: string; events: string[] }) =>
      apiFetch<Webhook>("/api/webhooks", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    update: (id: string, payload: Partial<Webhook>) =>
      apiFetch<Webhook>(`/api/webhooks/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) =>
      apiFetch<{ status: string }>(`/api/webhooks/${id}`, { method: "DELETE" }),
    test: (id: string) =>
      apiFetch<{ status: string }>(`/api/webhooks/${id}/test`, {
        method: "POST",
      }),
  },
  spamReports: {
    reportSpam: (payload: { email_uid: string; from_address: string }) =>
      apiFetch<{ status: string }>("/api/mail/report/spam", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    reportNotSpam: (payload: { email_uid: string; from_address: string }) =>
      apiFetch<{ status: string }>("/api/mail/report/not-spam", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
  ediscovery: {
    exports: () =>
      apiFetch<EdiscoveryExport[]>("/api/admin/ediscovery/exports"),
    create: (payload: Record<string, unknown>) =>
      apiFetch<EdiscoveryExport>("/api/admin/ediscovery/export", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
  whitelabel: {
    get: (domain?: string) =>
      apiFetch<Whitelabel>(
        domain
          ? `/api/admin/whitelabel?domain=${encodeURIComponent(domain)}`
          : "/api/admin/whitelabel",
      ),
    update: (payload: Whitelabel) =>
      apiFetch<Whitelabel>("/api/admin/whitelabel", {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
  },
};
