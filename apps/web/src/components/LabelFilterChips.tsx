import { sortLabelsByImpact, labelTitle } from "../lib/searchScoring";
import { cn } from "@/lib/utils";

const ALL = ["offer", "interview", "rejection"] as const;
type L = (typeof ALL)[number];

export function LabelFilterChips({
  value = [],
  onChange,
}: { value?: string[]; onChange: (next: string[]) => void }) {
  const current = new Set(value);
  const ordered = sortLabelsByImpact(ALL as unknown as string[]) as L[];

  function toggle(l: L) {
    const next = new Set(current);
    if (next.has(l)) next.delete(l);
    else next.add(l);
    onChange(Array.from(next));
  }

  function clearAll() {
    onChange([]);
  }

  return (
    <div className="flex items-center gap-2">
      {ordered.map((l) => {
        const active = current.has(l);
        return (
          <button
            key={l}
            type="button"
            onClick={() => toggle(l)}
            data-testid={`filter-label-${l}`}
            className={cn(
              "filter-pill",
              l === "offer" && "filter-pill-offer",
              l === "interview" && "filter-pill-interview",
              l === "rejection" && "filter-pill-rejection",
              active && "filter-pill-semantic-active"
            )}
            title={labelTitle(l)}
          >
            {labelTitle(l)}
          </button>
        );
      })}
      {current.size > 0 && (
        <button type="button" onClick={clearAll} className="text-xs text-muted-foreground underline">
          Clear
        </button>
      )}
    </div>
  );
}
