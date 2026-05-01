"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/api";

type AutoresponderPayload = {
  is_enabled: boolean;
  subject: string;
  body: string;
  start_date?: string | null;
  end_date?: string | null;
  reply_once_per_sender: boolean;
};

export function AutoresponderSettings() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const [enabled, setEnabled] = useState(false);
  const [subject, setSubject] = useState("Out of Office");
  const [body, setBody] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [replyOncePerSender, setReplyOncePerSender] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const current = await apiFetch<AutoresponderPayload | null>(
          "/api/mail/autoresponder",
        );
        if (current) {
          setEnabled(current.is_enabled);
          setSubject(current.subject || "Out of Office");
          setBody(current.body || "");
          setStartDate(current.start_date || "");
          setEndDate(current.end_date || "");
          setReplyOncePerSender(Boolean(current.reply_once_per_sender));
        }
      } catch {
        setMessage("Failed to load autoresponder settings");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const save = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await apiFetch<{ status: string }>("/api/mail/autoresponder", {
        method: "PUT",
        body: JSON.stringify({
          is_enabled: enabled,
          subject,
          body,
          start_date: startDate || null,
          end_date: endDate || null,
          reply_once_per_sender: replyOncePerSender,
        }),
      });
      setMessage("Autoresponder settings saved");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Failed to save autoresponder settings",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="space-y-4 rounded-3xl border border-black/10 bg-white/90 p-5 shadow-panel">
      <div>
        <h2 className="text-xl font-semibold text-ink">Autoresponder</h2>
        <p className="text-sm text-ink/60">
          Automatically reply when you are away.
        </p>
      </div>

      {loading ? (
        <p className="text-sm text-ink/60">Loading settings...</p>
      ) : null}

      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(event) => setEnabled(event.target.checked)}
        />
        Enable autoresponder
      </label>

      <Input
        value={subject}
        onChange={(event) => setSubject(event.target.value)}
        placeholder="Subject"
      />

      <textarea
        className="min-h-32 w-full rounded-2xl border border-black/10 bg-white/80 px-4 py-3 text-sm text-ink outline-none focus:border-ember"
        value={body}
        onChange={(event) => setBody(event.target.value)}
        placeholder="Message body"
      />

      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs uppercase tracking-wide text-ink/60">
            Start Date
          </label>
          <Input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs uppercase tracking-wide text-ink/60">
            End Date
          </label>
          <Input
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
          />
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          checked={replyOncePerSender}
          onChange={(event) => setReplyOncePerSender(event.target.checked)}
        />
        Reply only once per sender
      </label>

      <div className="flex items-center gap-3">
        <Button type="button" onClick={save} disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </Button>
        {message ? <p className="text-sm text-ink/70">{message}</p> : null}
      </div>
    </section>
  );
}
