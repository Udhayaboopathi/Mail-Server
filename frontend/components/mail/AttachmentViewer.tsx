import type { Attachment } from "@/types";

export function AttachmentViewer({
  attachments,
}: {
  attachments: Attachment[];
}) {
  if (attachments.length === 0) {
    return null;
  }
  return (
    <div className="space-y-2 rounded-3xl border border-black/10 bg-paper p-4">
      <p className="text-sm font-semibold text-ink">Attachments</p>
      {attachments.map((attachment) => (
        <a
          key={attachment.filename}
          className="block rounded-2xl bg-white px-4 py-3 text-sm text-ember"
          href={`data:${attachment.mime_type};base64,${attachment.content_base64}`}
          download={attachment.filename}
        >
          {attachment.filename}
        </a>
      ))}
    </div>
  );
}
