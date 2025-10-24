import { sortLabelsByImpact, labelTitle } from "../lib/searchScoring";

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
            className={
              "inline-flex items-center rounded-full px-2 py-0.5 text-xs ring-1 transition " +
              (l === "offer"
                ? "ring-yellow-300 " + (active ? "bg-yellow-200" : "bg-yellow-100")
                : l === "interview"
                ? "ring-green-300 " + (active ? "bg-green-200" : "bg-green-100")
                : "ring-gray-300 " + (active ? "bg-gray-200" : "bg-gray-100"))
            }
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
