"use client";

import { useEffect, useState } from "react";

import { StatsCard } from "@/components/admin/StatsCard";
import { api } from "@/lib/api";
import type { Stats } from "@/types";

export default function AdminHomePage() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    api.admin
      .stats()
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  if (stats === null) {
    return (
      <div className="rounded-3xl border border-dashed border-black/15 bg-white/80 p-8 text-sm text-ink/60">
        Loading stats...
      </div>
    );
  }

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-ember">Admin</p>
        <h1 className="text-3xl font-semibold text-ink">Dashboard</h1>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <StatsCard
          label="Total users"
          value={stats.total_users}
          tone="accent"
        />
        <StatsCard label="Total domains" value={stats.total_domains} />
        <StatsCard label="Mailboxes" value={stats.total_mailboxes} />
        <StatsCard label="Audit logs" value={stats.audit_logs} />
        <StatsCard label="Mail today" value={stats.mail_volume_today} />
        <StatsCard label="Storage MB" value={stats.storage_used_mb} />
      </div>
    </section>
  );
}
