"use client";

import DOMPurify from "dompurify";

import { AttachmentViewer } from "@/components/mail/AttachmentViewer";
import { Badge } from "@/components/ui/Badge";
import type { MailMessage } from "@/types";

export function EmailReader({ message }: { message: MailMessage }) {
  const safeHtml = message.body_html
    ? DOMPurify.sanitize(message.body_html)
    : "";

  return (
    <div className="space-y-6 rounded-3xl border border-black/10 bg-white/90 p-6 shadow-panel">
      <header className="space-y-3 border-b border-black/10 pb-5">
        <div className="flex flex-wrap items-center gap-2 text-sm text-ink/60">
          <span>From: {message.headers.from}</span>
          <span>To: {message.headers.to}</span>
          {message.headers.cc ? <span>Cc: {message.headers.cc}</span> : null}
        </div>
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold text-ink">
            {message.headers.subject}
          </h1>
          <Badge>{message.flags.join(", ")}</Badge>
        </div>
      </header>
      {safeHtml ? (
        <iframe
          title="Email body"
          className="min-h-[320px] w-full rounded-3xl border border-black/10 bg-white"
          sandbox="allow-popups"
          srcDoc={safeHtml}
        />
      ) : (
        <pre className="whitespace-pre-wrap rounded-3xl bg-paper p-4 text-sm text-ink/80">
          {message.body_text ?? ""}
        </pre>
      )}
      <AttachmentViewer attachments={message.attachments} />
    </div>
  );
}
