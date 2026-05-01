import { Badge } from "@/components/ui/Badge";

export function StatsCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  tone?: "neutral" | "accent";
}) {
  return (
    <div className="rounded-3xl border border-black/10 bg-white/90 p-5 shadow-panel">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-ink/50">
            {label}
          </p>
          <p className="mt-2 text-3xl font-semibold text-ink">{value}</p>
        </div>
        <Badge className={tone === "accent" ? "bg-ember text-white" : ""}>
          {tone}
        </Badge>
      </div>
    </div>
  );
}
