"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/api";

type BackupJob = {
  id: string;
  type: string;
  status: string;
  file_size_mb?: number | null;
  total_messages?: number | null;
  created_at?: string;
};

export function BackupManager() {
  const [jobs, setJobs] = useState<BackupJob[]>([]);
  const [statusText, setStatusText] = useState<string | null>(null);
  const [restoreFile, setRestoreFile] = useState<File | null>(null);

  const loadJobs = async () => {
    const response = await apiFetch<BackupJob[]>("/api/admin/backup/jobs");
    setJobs(response);
  };

  useEffect(() => {
    void loadJobs();
    const timer = window.setInterval(() => {
      void loadJobs();
    }, 3000);
    return () => window.clearInterval(timer);
  }, []);

  const createBackup = async () => {
    setStatusText("Starting backup...");
    const result = await apiFetch<{ job_id: string; status: string }>(
      "/api/admin/backup/full",
      { method: "POST" },
    );
    setStatusText(`Backup job started: ${result.job_id}`);
    await loadJobs();
  };

  const restoreBackup = async () => {
    if (!restoreFile) {
      setStatusText("Select a .tar.gz backup file first");
      return;
    }
    const formData = new FormData();
    formData.append("backup_file", restoreFile);

    const token =
      (typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null) || "";
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/admin/backup/restore`,
      {
        method: "POST",
        body: formData,
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        credentials: "include",
      },
    );
    const data = await response.json();
    if (!response.ok) {
      setStatusText(typeof data === "string" ? data : JSON.stringify(data));
      return;
    }
    setStatusText(`Restore status: ${data.status}`);
    await loadJobs();
  };

  const download = (jobId: string) => {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "";
    window.open(`${base}/api/admin/backup/${jobId}/download`, "_blank");
  };

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-ink">Backup Manager</h1>
        <p className="text-sm text-ink/60">
          Automatic daily backup at 2:00 AM UTC.
        </p>
      </div>

      <div className="rounded-3xl border border-black/10 bg-white/90 p-5 shadow-panel">
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => void createBackup()}>
            Create Full Backup
          </Button>
          {statusText ? (
            <p className="text-sm text-ink/70">{statusText}</p>
          ) : null}
        </div>
      </div>

      <div className="rounded-3xl border border-black/10 bg-white/90 p-5 shadow-panel space-y-3">
        <h2 className="text-xl font-semibold text-ink">Restore</h2>
        <Input
          type="file"
          accept=".tar.gz"
          onChange={(event) => setRestoreFile(event.target.files?.[0] ?? null)}
        />
        <Button
          className="bg-sand text-ink"
          onClick={() => void restoreBackup()}
        >
          Restore Backup
        </Button>
      </div>

      <div className="overflow-hidden rounded-3xl border border-black/10 bg-white/90 shadow-panel">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-paper text-ink/60">
            <tr>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Size</th>
              <th className="px-4 py-3">Messages</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Download</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id} className="border-t border-black/5">
                <td className="px-4 py-3">{job.type}</td>
                <td className="px-4 py-3">{job.status}</td>
                <td className="px-4 py-3">
                  {job.file_size_mb ? `${job.file_size_mb.toFixed(2)} MB` : "-"}
                </td>
                <td className="px-4 py-3">{job.total_messages ?? "-"}</td>
                <td className="px-4 py-3">
                  {job.created_at
                    ? new Date(job.created_at).toLocaleString()
                    : "-"}
                </td>
                <td className="px-4 py-3">
                  <Button
                    className="bg-ember"
                    onClick={() => download(job.id)}
                    disabled={job.status !== "done"}
                  >
                    Download
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
