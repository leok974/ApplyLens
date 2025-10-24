import { Switch } from "@/components/ui/switch"
import { ShieldAlert, ShieldX } from "lucide-react"

type Props = {
  highRisk: boolean
  onHighRiskChange: (v: boolean) => void
  quarantinedOnly: boolean
  onQuarantinedOnlyChange: (v: boolean) => void
}

export function SecurityFilterControls({
  highRisk,
  onHighRiskChange,
  quarantinedOnly,
  onQuarantinedOnlyChange,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-3">
      <span className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
        <ShieldAlert className="h-4 w-4" />
        Security filters:
      </span>

      {/* High-Risk chip */}
      <label
        data-testid="chip-high-risk"
        className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm cursor-pointer transition-colors ${
          highRisk
            ? "bg-red-500/15 border-red-600/30 text-red-300 hover:bg-red-500/20"
            : "bg-muted/30 hover:bg-muted/50"
        }`}
      >
        <Switch checked={highRisk} onCheckedChange={onHighRiskChange} data-testid="filter-high-risk" />
        <span className="flex items-center gap-1.5">
          <ShieldAlert className="h-3.5 w-3.5" />
          High Risk (≥80)
        </span>
      </label>

      {/* Quarantined only */}
      <label
        data-testid="chip-quarantined"
        className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm cursor-pointer transition-colors ${
          quarantinedOnly
            ? "bg-amber-500/15 border-amber-600/30 text-amber-300 hover:bg-amber-500/20"
            : "bg-muted/30 hover:bg-muted/50"
        }`}
      >
        <Switch checked={quarantinedOnly} onCheckedChange={onQuarantinedOnlyChange} data-testid="filter-quarantined" />
        <span className="flex items-center gap-1.5">
          <ShieldX className="h-3.5 w-3.5" />
          Quarantined only
        </span>
      </label>

      {(highRisk || quarantinedOnly) && (
        <button
          type="button"
          onClick={() => {
            onHighRiskChange(false)
            onQuarantinedOnlyChange(false)
          }}
          className="ml-2 text-xs text-muted-foreground hover:text-foreground underline"
        >
          Clear filters
        </button>
      )}
    </div>
  )
}
