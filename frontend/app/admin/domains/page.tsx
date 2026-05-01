"use client";

import { type FormEvent, useEffect, useState } from "react";

import { DNSSetupModal } from "@/components/admin/DNSSetupModal";
import { DomainUsersModal } from "@/components/admin/DomainUsersModal";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";

type DomainRow = {
  id: string;
  name: string;
  is_active: boolean;
  dkim_selector: string;
  dns_verified: boolean;
  cloudflare_zone_id?: string | null;
  created_at?: string;
};

export default function DomainsPage() {
  const [domains, setDomains] = useState<DomainRow[]>([]);
  const [domainName, setDomainName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dnsModalDomain, setDnsModalDomain] = useState<DomainRow | null>(null);
  const [usersModalDomain, setUsersModalDomain] = useState<DomainRow | null>(
    null,
  );

  async function loadDomains() {
    try {
      const result = await api.domains.list();
      setDomains(result as DomainRow[]);
    } catch {
      setDomains([]);
    }
  }

  useEffect(() => {
    void loadDomains();
  }, []);

  async function handleCreateDomain(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = domainName.trim().toLowerCase();
    if (!name) {
      setError("Enter a domain name");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await api.domains.create(name);
      setDomainName("");
      await loadDomains();
    } catch (createError) {
      setError(
        createError instanceof Error
          ? createError.message
          : "Failed to add domain",
      );
    } finally {
      setCreating(false);
    }
  }

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-ember">Admin</p>
        <h1 className="text-3xl font-semibold text-ink">Domains</h1>
      </div>

      <form
        onSubmit={handleCreateDomain}
        className="flex flex-col gap-3 rounded-3xl border border-black/10 bg-white/90 p-4 shadow-panel sm:flex-row"
      >
        <input
          className="min-h-11 flex-1 rounded-2xl border border-black/10 bg-paper px-4 text-sm outline-none transition focus:border-ember"
          placeholder="example.com"
          value={domainName}
          onChange={(event) => setDomainName(event.target.value)}
        />
        <Button type="submit" disabled={creating}>
          {creating ? "Adding..." : "Add domain"}
        </Button>
        {error ? (
          <p className="text-sm text-ember sm:self-center">{error}</p>
        ) : null}
      </form>

      <div className="overflow-hidden rounded-3xl border border-black/10 bg-white/90 shadow-panel">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-paper text-ink/60">
            <tr>
              <th className="px-4 py-3">Domain</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">DNS Verified</th>
              <th className="px-4 py-3">Selector</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {domains.map((domain) => (
              <tr key={domain.id} className="border-t border-black/5">
                <td className="px-4 py-3 font-medium text-ink">
                  {domain.name}
                </td>
                <td className="px-4 py-3 text-ink/70">
                  {domain.is_active ? "Active" : "Disabled"}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${domain.dns_verified ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}
                  >
                    {domain.dns_verified ? "Verified" : "Not verified"}
                  </span>
                </td>
                <td className="px-4 py-3 text-ink/70">
                  {domain.dkim_selector}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      className="bg-ink"
                      onClick={() => setDnsModalDomain(domain)}
                    >
                      DNS Setup
                    </Button>
                    <Button
                      type="button"
                      className="bg-ember"
                      onClick={() => setUsersModalDomain(domain)}
                    >
                      Add User
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {dnsModalDomain ? (
        <DNSSetupModal
          domain={dnsModalDomain}
          onClose={() => setDnsModalDomain(null)}
        />
      ) : null}

      {usersModalDomain ? (
        <DomainUsersModal
          domain={usersModalDomain}
          onClose={() => setUsersModalDomain(null)}
        />
      ) : null}
    </section>
  );
}
