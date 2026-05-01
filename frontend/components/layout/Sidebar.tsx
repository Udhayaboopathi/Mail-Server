import Link from "next/link";

import { Badge } from "@/components/ui/Badge";

const folders = ["Inbox", "Sent", "Drafts", "Trash", "Spam"];

export function Sidebar({ unreadCount = 12 }: { unreadCount?: number }) {
  return (
    <aside className="hidden h-full w-72 flex-col border-r border-black/10 bg-white/80 p-5 backdrop-blur lg:flex">
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-ember">
          Mail Stack
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-ink">Mailbox</h2>
      </div>
      <nav className="space-y-2">
        {folders.map((folder) => (
          <Link
            key={folder}
            href={`/mail/${folder.toLowerCase()}`}
            className="flex items-center justify-between rounded-2xl px-4 py-3 text-sm font-medium text-ink transition hover:bg-paper"
          >
            <span>{folder}</span>
            {folder === "Inbox" ? (
              <Badge className="bg-ember text-white">{unreadCount}</Badge>
            ) : null}
          </Link>
        ))}
      </nav>
      <div className="mt-auto rounded-3xl bg-ink p-4 text-paper shadow-panel">
        <p className="text-sm font-semibold">
          Self-hosted, no third-party relay.
        </p>
        <p className="mt-2 text-xs leading-5 text-paper/70">
          Operate SMTP, IMAP, auth, and storage on your own infrastructure.
        </p>
      </div>
    </aside>
  );
}
