import Link from "next/link";

import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import type { MailSummary } from "@/types";

export function EmailListItem({
  folder,
  mail,
}: {
  folder: string;
  mail: MailSummary;
}) {
  return (
    <Link
      href={`/mail/${folder}/${mail.uid}`}
      className="grid grid-cols-[auto_1fr_auto] gap-4 rounded-3xl border border-black/10 bg-white/85 p-4 transition hover:-translate-y-0.5 hover:shadow-panel"
    >
      <Avatar name={mail.sender} />
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <p className="truncate font-semibold text-ink">{mail.sender}</p>
          {mail.flags.includes("\\Seen") ? null : (
            <span className="h-2 w-2 rounded-full bg-ember" />
          )}
        </div>
        <p className="truncate text-sm text-ink/70">{mail.subject}</p>
        <p className="mt-1 truncate text-xs text-ink/50">{mail.preview}</p>
      </div>
      <div className="flex flex-col items-end gap-2 text-right text-xs text-ink/50">
        <span>{mail.date ?? "Now"}</span>
        {mail.has_attachments ? <Badge>Attachment</Badge> : null}
      </div>
    </Link>
  );
}
