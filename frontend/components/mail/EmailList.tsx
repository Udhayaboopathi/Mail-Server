"use client";

import { useMemo, useState } from "react";

import { EmailListItem } from "@/components/mail/EmailListItem";
import { useMail } from "@/hooks/useMail";
import type { MailSummary } from "@/types";

export function EmailList({ folder }: { folder: string }) {
  const [page, setPage] = useState(1);
  const { data } = useMail(folder, page);
  const emails = useMemo(() => (data ?? []) as MailSummary[], [data]);

  return (
    <div className="space-y-3">
      {emails.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-black/15 bg-white/70 p-8 text-sm text-ink/60">
          No messages in this folder yet.
        </div>
      ) : null}
      {emails.map((mail: MailSummary) => (
        <EmailListItem key={mail.id} folder={folder} mail={mail} />
      ))}
      <button
        className="mx-auto block rounded-full border border-black/10 px-4 py-2 text-sm text-ink/70"
        onClick={() => setPage((value) => value + 1)}
      >
        Load more
      </button>
    </div>
  );
}
