"use client";

import { useEffect, useMemo, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { apiFetch } from "@/lib/api";

type ContactSuggestion = {
  id?: string | null;
  email: string;
  name?: string | null;
};

export function ComposeModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [to, setTo] = useState("");
  const [cc, setCc] = useState("");
  const [bcc, setBcc] = useState("");
  const [subject, setSubject] = useState("");
  const [customScheduleAt, setCustomScheduleAt] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [undoId, setUndoId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<ContactSuggestion[]>([]);
  const [activeField, setActiveField] = useState<"to" | "cc" | "bcc" | null>(
    null,
  );

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: "Write your message..." }),
    ],
    content: "<p></p>",
  });

  const toList = useMemo(
    () =>
      to
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
    [to],
  );
  const ccList = useMemo(
    () =>
      cc
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
    [cc],
  );
  const bccList = useMemo(
    () =>
      bcc
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
    [bcc],
  );

  const bodyText = editor?.getText() ?? "";
  const bodyHtml = editor?.getHTML() ?? "";

  useEffect(() => {
    if (open) {
      const timeout = window.setTimeout(() => undefined, 30000);
      return () => window.clearTimeout(timeout);
    }
    return undefined;
  }, [open]);

  const loadSuggestions = async (value: string) => {
    const query = value.split(",").pop()?.trim() ?? "";
    if (query.length < 2) {
      setSuggestions([]);
      return;
    }
    try {
      const items = await apiFetch<ContactSuggestion[]>(
        `/api/contacts?q=${encodeURIComponent(query)}`,
      );
      setSuggestions(items);
    } catch {
      setSuggestions([]);
    }
  };

  const applySuggestion = (email: string) => {
    const apply = (current: string, setter: (value: string) => void) => {
      const parts = current.split(",");
      parts[parts.length - 1] = ` ${email}`;
      setter(parts.join(",").replace(/^\s+/, ""));
    };
    if (activeField === "to") {
      apply(to, setTo);
    }
    if (activeField === "cc") {
      apply(cc, setCc);
    }
    if (activeField === "bcc") {
      apply(bcc, setBcc);
    }
    setSuggestions([]);
  };

  const sendWithUndo = async () => {
    const response = await apiFetch<{ id?: string; undo_expires_at?: string }>(
      "/api/mail/send?undo_window=10",
      {
        method: "POST",
        body: JSON.stringify({
          to: toList,
          cc: ccList,
          bcc: bccList,
          subject,
          body_text: bodyText,
          body_html: bodyHtml,
          attachments: [],
        }),
      },
    );
    if (response.id) {
      setUndoId(response.id);
      setToast("Sending in 10s... Undo");
      window.setTimeout(() => {
        setUndoId(null);
        setToast(null);
      }, 10000);
    }
  };

  const undoSend = async () => {
    if (!undoId) {
      return;
    }
    const result = await apiFetch<{ cancelled: boolean; message: string }>(
      `/api/mail/send/${undoId}/undo`,
      {
        method: "DELETE",
      },
    );
    setToast(result.message);
    setUndoId(null);
  };

  const scheduleAt = async (targetDate: Date) => {
    await apiFetch<{ id: string; send_at: string; status: string }>(
      "/api/mail/schedule",
      {
        method: "POST",
        body: JSON.stringify({
          to: toList,
          cc: ccList,
          bcc: bccList,
          subject,
          body_text: bodyText,
          body_html: bodyHtml,
          attachments: [],
          send_at: targetDate.toISOString(),
        }),
      },
    );
    setToast(`Email scheduled for ${targetDate.toLocaleString()}`);
  };

  const scheduleInOneHour = async () => {
    const d = new Date(Date.now() + 60 * 60 * 1000);
    await scheduleAt(d);
  };

  const scheduleTomorrow8am = async () => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    d.setHours(8, 0, 0, 0);
    await scheduleAt(d);
  };

  const scheduleCustom = async () => {
    if (!customScheduleAt) {
      return;
    }
    await scheduleAt(new Date(customScheduleAt));
  };

  return (
    <Modal open={open} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-ink">Compose</h2>
          <Button className="bg-sand text-ink" onClick={onClose}>
            Close
          </Button>
        </div>
        <Input
          value={to}
          onChange={(event) => {
            setActiveField("to");
            setTo(event.target.value);
            void loadSuggestions(event.target.value);
          }}
          placeholder="To"
        />
        <Input
          value={cc}
          onChange={(event) => {
            setActiveField("cc");
            setCc(event.target.value);
            void loadSuggestions(event.target.value);
          }}
          placeholder="CC"
        />
        <Input
          value={bcc}
          onChange={(event) => {
            setActiveField("bcc");
            setBcc(event.target.value);
            void loadSuggestions(event.target.value);
          }}
          placeholder="BCC"
        />

        {suggestions.length > 0 ? (
          <div className="max-h-40 overflow-auto rounded-2xl border border-black/10 bg-white p-2">
            {suggestions.map((item, index) => (
              <button
                key={`${item.email}-${index}`}
                type="button"
                className="block w-full rounded-xl px-3 py-2 text-left text-sm text-ink hover:bg-paper"
                onClick={() => applySuggestion(item.email)}
              >
                {item.name ? `${item.name} <${item.email}>` : item.email}
              </button>
            ))}
          </div>
        ) : null}

        <Input
          value={subject}
          onChange={(event) => setSubject(event.target.value)}
          placeholder="Subject"
        />
        <div className="rounded-3xl border border-black/10 bg-paper p-4">
          {editor ? <EditorContent editor={editor} /> : null}
        </div>
        {toast ? (
          <div className="flex items-center justify-between rounded-2xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            <span>{toast}</span>
            {undoId ? (
              <Button
                type="button"
                className="bg-sand text-ink"
                onClick={() => void undoSend()}
              >
                Undo
              </Button>
            ) : null}
          </div>
        ) : null}

        <div className="flex flex-wrap gap-3">
          <Button
            className="bg-ember"
            type="button"
            onClick={() => void sendWithUndo()}
          >
            Send
          </Button>
          <Button
            className="bg-ink"
            type="button"
            onClick={() => void scheduleInOneHour()}
          >
            Schedule: In 1 hour
          </Button>
          <Button
            className="bg-ink"
            type="button"
            onClick={() => void scheduleTomorrow8am()}
          >
            Schedule: Tomorrow 8am
          </Button>
          <div className="flex items-center gap-2">
            <Input
              type="datetime-local"
              value={customScheduleAt}
              onChange={(event) => setCustomScheduleAt(event.target.value)}
            />
            <Button
              className="bg-ink"
              type="button"
              onClick={() => void scheduleCustom()}
            >
              Schedule Custom
            </Button>
          </div>
          <Button className="bg-sand text-ink">Save draft</Button>
        </div>
      </div>
    </Modal>
  );
}
