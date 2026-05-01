"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api";

type ScheduledItem = {
  id: string;
  to_addresses: string[];
  subject: string;
  send_at: string;
  status: string;
};

export function ScheduledList() {
  const [items, setItems] = useState<ScheduledItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch<ScheduledItem[]>("/api/mail/scheduled");
      setItems(response);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Failed to load scheduled emails",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const cancel = async (id: string) => {
    await apiFetch(`/api/mail/scheduled/${id}`, { method: "DELETE" });
    await load();
  };

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-3xl font-semibold text-ink">Scheduled</h1>
        <p className="text-sm text-ink/60">
          Pending emails waiting to be sent.
        </p>
      </div>

      {loading ? <p className="text-sm text-ink/60">Loading...</p> : null}
      {error ? <p className="text-sm text-red-700">{error}</p> : null}

      <div className="overflow-hidden rounded-3xl border border-black/10 bg-white/90 shadow-panel">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-paper text-ink/60">
            <tr>
              <th className="px-4 py-3">To</th>
              <th className="px-4 py-3">Subject</th>
              <th className="px-4 py-3">Scheduled for</th>
              <th className="px-4 py-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td className="px-4 py-3 text-ink/60" colSpan={4}>
                  No scheduled emails.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id} className="border-t border-black/5">
                  <td className="px-4 py-3 text-ink">
                    {item.to_addresses.join(", ")}
                  </td>
                  <td className="px-4 py-3 text-ink/70">{item.subject}</td>
                  <td className="px-4 py-3 text-ink/70">
                    {new Date(item.send_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <Button
                      className="bg-sand text-ink"
                      type="button"
                      onClick={() => void cancel(item.id)}
                    >
                      Cancel
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
