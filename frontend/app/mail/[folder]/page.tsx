"use client";

import { useParams } from "next/navigation";

import { EmailList } from "@/components/mail/EmailList";

export default function FolderPage() {
  const params = useParams<{ folder: string }>();
  const folder = Array.isArray(params.folder)
    ? params.folder[0]
    : params.folder;
  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-ember">Folder</p>
        <h1 className="text-3xl font-semibold text-ink">{folder}</h1>
      </div>
      <EmailList folder={folder} />
    </section>
  );
}
