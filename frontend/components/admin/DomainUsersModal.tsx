"use client";

import { type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { apiFetch } from "@/lib/api";

type DomainLike = {
  id: string;
  name: string;
};

type DomainUser = {
  id: string;
  full_address: string;
  local_part: string;
  quota_mb: number;
  used_mb: number;
  is_active: boolean;
  created_at?: string;
};

export function DomainUsersModal({
  domain,
  onClose,
}: {
  domain: DomainLike;
  onClose: () => void;
}) {
  const [users, setUsers] = useState<DomainUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [localPart, setLocalPart] = useState("");
  const [password, setPassword] = useState("");
  const [quotaMb, setQuotaMb] = useState("1024");
  const [submitting, setSubmitting] = useState(false);
  const [uploadingFor, setUploadingFor] = useState<string | null>(null);

  const downloadExport = (mailboxId: string, type: "mbox" | "zip") => {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "";
    window.open(`${base}/api/mailboxes/${mailboxId}/export/${type}`, "_blank");
  };

  const importFile = async (mailboxId: string, file: File) => {
    const ext = file.name.toLowerCase().endsWith(".mbox")
      ? "mbox"
      : file.name.toLowerCase().endsWith(".zip")
        ? "zip"
        : "";
    if (!ext) {
      setError("Import supports .mbox or .zip only");
      return;
    }

    setUploadingFor(mailboxId);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("import_file", file);
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/mailboxes/${mailboxId}/import/${ext}`,
        {
          method: "POST",
          credentials: "include",
          body: formData,
        },
      );
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text);
      }
      await loadUsers();
    } catch (importError) {
      setError(
        importError instanceof Error
          ? importError.message
          : "Failed to import mailbox data",
      );
    } finally {
      setUploadingFor(null);
    }
  };

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch<DomainUser[]>(
        `/api/domains/${domain.id}/users`,
      );
      setUsers(response);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Failed to load domain users",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadUsers();
  }, [domain.id]);

  const addUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await apiFetch<DomainUser>(`/api/domains/${domain.id}/users`, {
        method: "POST",
        body: JSON.stringify({
          local_part: localPart,
          password,
          quota_mb: Number.parseInt(quotaMb || "1024", 10),
        }),
      });
      setLocalPart("");
      setPassword("");
      setQuotaMb("1024");
      await loadUsers();
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Failed to create mailbox user",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open onClose={onClose} className="max-w-6xl">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-ink">Domain Users</h2>
            <p className="text-sm text-ink/60">{domain.name}</p>
          </div>
          <Button className="bg-sand text-ink" onClick={onClose}>
            Close
          </Button>
        </div>

        <form
          onSubmit={addUser}
          className="grid gap-3 rounded-2xl border border-black/10 bg-paper p-4 md:grid-cols-4"
        >
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wide text-ink/60">
              Local part
            </label>
            <div className="flex items-center gap-2">
              <Input
                value={localPart}
                onChange={(event) => setLocalPart(event.target.value)}
                placeholder="john"
              />
              <span className="text-sm text-ink/70">@{domain.name}</span>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wide text-ink/60">
              Password
            </label>
            <Input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 8 characters"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wide text-ink/60">
              Quota MB
            </label>
            <Input
              type="number"
              value={quotaMb}
              onChange={(event) => setQuotaMb(event.target.value)}
            />
          </div>
          <div className="flex items-end">
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Add User"}
            </Button>
          </div>
        </form>

        {error ? <p className="text-sm text-red-700">{error}</p> : null}

        <div className="overflow-hidden rounded-2xl border border-black/10 bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-paper text-ink/60">
              <tr>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Quota</th>
                <th className="px-3 py-2">Used</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Created</th>
                <th className="px-3 py-2">Export / Import</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td className="px-3 py-3 text-ink/60" colSpan={6}>
                    Loading users...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-ink/60" colSpan={6}>
                    No users in this domain yet.
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="border-t border-black/5">
                    <td className="px-3 py-2 font-medium text-ink">
                      {user.full_address}
                    </td>
                    <td className="px-3 py-2 text-ink/70">
                      {user.quota_mb} MB
                    </td>
                    <td className="px-3 py-2 text-ink/70">
                      {user.used_mb.toFixed(2)} MB
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${user.is_active ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}
                      >
                        {user.is_active ? "Active" : "Disabled"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-ink/70">
                      {user.created_at
                        ? new Date(user.created_at).toLocaleString()
                        : "-"}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          className="bg-ink"
                          onClick={() => downloadExport(user.id, "mbox")}
                        >
                          Export MBOX
                        </Button>
                        <Button
                          type="button"
                          className="bg-ember"
                          onClick={() => downloadExport(user.id, "zip")}
                        >
                          Export ZIP
                        </Button>
                        <label className="inline-flex cursor-pointer items-center rounded-2xl bg-sand px-3 py-2 text-sm text-ink">
                          {uploadingFor === user.id ? "Importing..." : "Import"}
                          <input
                            className="hidden"
                            type="file"
                            accept=".mbox,.zip"
                            onChange={(event: {
                              target: HTMLInputElement;
                              currentTarget: HTMLInputElement;
                            }) => {
                              const file = event.target.files?.[0];
                              if (file) {
                                void importFile(user.id, file);
                              }
                              event.currentTarget.value = "";
                            }}
                          />
                        </label>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Modal>
  );
}
