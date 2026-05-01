import type { Domain } from "@/types";

export function DomainTable({ domains }: { domains: Domain[] }) {
  return (
    <div className="overflow-hidden rounded-3xl border border-black/10 bg-white/90 shadow-panel">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-paper text-ink/60">
          <tr>
            <th className="px-4 py-3">Domain</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Selector</th>
          </tr>
        </thead>
        <tbody>
          {domains.map((domain) => (
            <tr key={domain.id} className="border-t border-black/5">
              <td className="px-4 py-3 font-medium text-ink">{domain.name}</td>
              <td className="px-4 py-3 text-ink/70">
                {domain.is_active ? "Active" : "Disabled"}
              </td>
              <td className="px-4 py-3 text-ink/70">{domain.dkim_selector}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
