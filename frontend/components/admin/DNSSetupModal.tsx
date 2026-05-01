"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { apiFetch } from "@/lib/api";

type DomainLike = {
  id: string;
  name: string;
  cloudflare_zone_id?: string | null;
};

type GuideRecord = {
  type: string;
  name: string;
  value: string;
  priority: string;
  ttl: string;
  purpose: string;
};

type GuideResponse = {
  domain: string;
  records: GuideRecord[];
  ptr_note: string;
  propagation_note: string;
  verify_commands: Record<string, string>;
};

type VerifyResponse = {
  mx: boolean;
  a: boolean;
  spf: boolean;
  dkim: boolean;
  dmarc: boolean;
  all_valid: boolean;
  verified_at?: string | null;
};

function StatusBadge({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${ok ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}
    >
      {ok ? "OK" : "Missing/Invalid"}
    </span>
  );
}

export function DNSSetupModal({
  domain,
  onClose,
}: {
  domain: DomainLike;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<"auto" | "manual">("auto");

  const [zoneId, setZoneId] = useState(domain.cloudflare_zone_id ?? "");
  const [autoLoading, setAutoLoading] = useState(false);
  const [autoResult, setAutoResult] = useState<{
    message: string;
    records: Record<string, unknown>;
  } | null>(null);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyResult, setVerifyResult] = useState<VerifyResponse | null>(null);
  const [autoError, setAutoError] = useState<string | null>(null);

  const [manualLoading, setManualLoading] = useState(false);
  const [manualError, setManualError] = useState<string | null>(null);
  const [guide, setGuide] = useState<GuideResponse | null>(null);
  const [showFullDKIM, setShowFullDKIM] = useState(false);

  const verifyCommandsText = useMemo(() => {
    if (!guide) {
      return "";
    }
    return [
      guide.verify_commands.mx,
      guide.verify_commands.spf,
      guide.verify_commands.dkim,
      guide.verify_commands.dmarc,
      guide.verify_commands.a,
    ].join("\n");
  }, [guide]);

  const copy = async (value: string) => {
    await navigator.clipboard.writeText(value);
  };

  const configureAuto = async () => {
    setAutoLoading(true);
    setAutoError(null);
    try {
      const response = await apiFetch<{
        success: boolean;
        records_created: Record<string, unknown>;
        message: string;
      }>(`/api/domains/${domain.id}/dns/auto`, {
        method: "POST",
        body: JSON.stringify({ cloudflare_zone_id: zoneId.trim() || null }),
      });
      setAutoResult({
        message: response.message,
        records: response.records_created,
      });
    } catch (error) {
      setAutoError(
        error instanceof Error
          ? error.message
          : "Failed to configure DNS automatically",
      );
    } finally {
      setAutoLoading(false);
    }
  };

  const verifyDns = async () => {
    setVerifyLoading(true);
    setAutoError(null);
    try {
      const response = await apiFetch<VerifyResponse>(
        `/api/domains/${domain.id}/dns/verify`,
        {
          method: "POST",
        },
      );
      setVerifyResult(response);
    } catch (error) {
      setAutoError(
        error instanceof Error ? error.message : "Failed to verify DNS",
      );
    } finally {
      setVerifyLoading(false);
    }
  };

  const loadGuide = async () => {
    setManualLoading(true);
    setManualError(null);
    try {
      const response = await apiFetch<GuideResponse>(
        `/api/domains/${domain.id}/dns/guide`,
      );
      setGuide(response);
    } catch (error) {
      setManualError(
        error instanceof Error
          ? error.message
          : "Failed to load manual DNS guide",
      );
    } finally {
      setManualLoading(false);
    }
  };

  return (
    <Modal open onClose={onClose} className="max-w-6xl">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-ink">DNS Setup</h2>
            <p className="text-sm text-ink/60">{domain.name}</p>
          </div>
          <Button className="bg-sand text-ink" onClick={onClose}>
            Close
          </Button>
        </div>

        <div className="flex gap-2">
          <Button
            className={tab === "auto" ? "bg-ink" : "bg-paper text-ink"}
            onClick={() => setTab("auto")}
            type="button"
          >
            Auto (Cloudflare)
          </Button>
          <Button
            className={tab === "manual" ? "bg-ink" : "bg-paper text-ink"}
            onClick={() => setTab("manual")}
            type="button"
          >
            Manual
          </Button>
        </div>

        {tab === "auto" ? (
          <div className="space-y-4 rounded-2xl border border-black/10 bg-paper p-4">
            <p className="text-sm text-ink/70">
              Your domain must already be added to Cloudflare. Find your Zone ID
              in Cloudflare dashboard, then open your domain overview on the
              right sidebar.
            </p>
            <div className="grid gap-3 md:grid-cols-[1fr_auto_auto]">
              <Input
                placeholder="Cloudflare Zone ID (optional)"
                value={zoneId}
                onChange={(event) => setZoneId(event.target.value)}
              />
              <Button
                type="button"
                onClick={configureAuto}
                disabled={autoLoading}
              >
                {autoLoading ? "Configuring..." : "Configure DNS automatically"}
              </Button>
              <Button
                type="button"
                className="bg-ember"
                onClick={verifyDns}
                disabled={verifyLoading}
              >
                {verifyLoading ? "Verifying..." : "Verify DNS"}
              </Button>
            </div>

            {autoError ? (
              <p className="text-sm text-red-700">{autoError}</p>
            ) : null}

            {autoResult ? (
              <div className="rounded-2xl border border-green-200 bg-green-50 p-3 text-sm text-green-700">
                <p className="font-medium">{autoResult.message}</p>
                <pre className="mt-2 overflow-auto whitespace-pre-wrap text-xs text-green-800">
                  {JSON.stringify(autoResult.records, null, 2)}
                </pre>
              </div>
            ) : null}

            {verifyResult ? (
              <div className="space-y-2 rounded-2xl border border-black/10 bg-white p-3">
                <h3 className="text-sm font-semibold text-ink">
                  Verification Status
                </h3>
                <div className="grid gap-2 md:grid-cols-5">
                  <div className="flex items-center justify-between rounded-xl border border-black/10 p-2">
                    <span className="text-sm text-ink">MX</span>
                    <StatusBadge ok={verifyResult.mx} />
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-black/10 p-2">
                    <span className="text-sm text-ink">A</span>
                    <StatusBadge ok={verifyResult.a} />
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-black/10 p-2">
                    <span className="text-sm text-ink">SPF</span>
                    <StatusBadge ok={verifyResult.spf} />
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-black/10 p-2">
                    <span className="text-sm text-ink">DKIM</span>
                    <StatusBadge ok={verifyResult.dkim} />
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-black/10 p-2">
                    <span className="text-sm text-ink">DMARC</span>
                    <StatusBadge ok={verifyResult.dmarc} />
                  </div>
                </div>
                <p className="text-xs text-ink/60">
                  Overall:{" "}
                  {verifyResult.all_valid
                    ? "All records valid"
                    : "Some records are missing or incorrect"}
                </p>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="space-y-4 rounded-2xl border border-black/10 bg-paper p-4">
            <div className="flex items-center gap-3">
              <Button
                type="button"
                onClick={loadGuide}
                disabled={manualLoading}
              >
                {manualLoading ? "Loading..." : "Load DNS Records"}
              </Button>
              {guide ? (
                <Button
                  type="button"
                  className="bg-sand text-ink"
                  onClick={() => copy(verifyCommandsText)}
                >
                  Copy Verify Commands
                </Button>
              ) : null}
            </div>

            {manualError ? (
              <p className="text-sm text-red-700">{manualError}</p>
            ) : null}

            {guide ? (
              <>
                <div className="overflow-x-auto rounded-2xl border border-black/10 bg-white">
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-paper text-ink/60">
                      <tr>
                        <th className="px-3 py-2">Type</th>
                        <th className="px-3 py-2">Name</th>
                        <th className="px-3 py-2">Value</th>
                        <th className="px-3 py-2">Priority</th>
                        <th className="px-3 py-2">TTL</th>
                        <th className="px-3 py-2">Purpose</th>
                      </tr>
                    </thead>
                    <tbody>
                      {guide.records.map((record, index) => {
                        const isDKIM = record.name.includes("._domainkey.");
                        const shortValue =
                          isDKIM && !showFullDKIM
                            ? `${record.value.slice(0, 64)}...`
                            : record.value;
                        return (
                          <tr
                            key={`${record.type}-${record.name}-${index}`}
                            className="border-t border-black/5 align-top"
                          >
                            <td className="px-3 py-2">{record.type}</td>
                            <td className="px-3 py-2">{record.name}</td>
                            <td className="px-3 py-2">
                              <div className="space-y-1">
                                <div className="break-all text-xs text-ink">
                                  {shortValue}
                                </div>
                                <div className="flex gap-2">
                                  <button
                                    type="button"
                                    className="text-xs text-ember hover:underline"
                                    onClick={() => copy(record.value)}
                                  >
                                    Copy
                                  </button>
                                  {isDKIM ? (
                                    <button
                                      type="button"
                                      className="text-xs text-ink/70 hover:underline"
                                      onClick={() =>
                                        setShowFullDKIM((prev) => !prev)
                                      }
                                    >
                                      {showFullDKIM ? "Show less" : "Show full"}
                                    </button>
                                  ) : null}
                                </div>
                              </div>
                            </td>
                            <td className="px-3 py-2">{record.priority}</td>
                            <td className="px-3 py-2">{record.ttl}</td>
                            <td className="px-3 py-2 text-xs text-ink/70">
                              {record.purpose}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="rounded-2xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
                  {guide.ptr_note}
                </div>

                <div className="rounded-2xl border border-sky-300 bg-sky-50 p-3 text-sm text-sky-800">
                  {guide.propagation_note}
                </div>

                <div className="rounded-2xl border border-black/10 bg-white p-3">
                  <pre className="overflow-auto whitespace-pre-wrap text-xs text-ink">
                    {verifyCommandsText}
                  </pre>
                </div>
              </>
            ) : null}
          </div>
        )}
      </div>
    </Modal>
  );
}
