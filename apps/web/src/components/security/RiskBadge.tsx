import { Badge } from "@/components/ui/badge";
import { ShieldAlert, ShieldCheck } from "lucide-react";

export function RiskBadge({ score, quarantined }: { score: number; quarantined?: boolean }) {
  const level = score >= 80 ? "high" : score >= 40 ? "med" : "low";
  const color =
    level === "high" ? "bg-red-500/20 text-red-300 border-red-600/40" :
    level === "med"  ? "bg-amber-500/20 text-amber-300 border-amber-600/40" :
                       "bg-emerald-500/20 text-emerald-300 border-emerald-600/40";

  const Icon = level === "low" ? ShieldCheck : ShieldAlert;
  const title =
    (quarantined ? "Quarantined • " : "") +
    (level === "high" ? "High risk" : level === "med" ? "Medium risk" : "Low risk");

  return (
    <Badge
      data-testid="risk-badge"
      variant="outline"
      className={`gap-1 border ${color} px-2.5 py-1 rounded-full`}
      title={title}
    >
      <Icon className="h-3.5 w-3.5" />
      <span className="tabular-nums">{score}</span>
    </Badge>
  );
}
