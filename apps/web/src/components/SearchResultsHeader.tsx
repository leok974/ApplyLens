import { RECENCY_HINT } from "../lib/searchScoring";
import { getRecencyScale } from "../state/searchPrefs";

type Props = { query: string; total?: number; showHint?: boolean };

export default function SearchResultsHeader({ query, total, showHint }: Props) {
  const scale = getRecencyScale();
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-end justify-between">
        <h2 className="text-lg font-semibold">
          Results{typeof total === "number" ? ` (${total})` : ""} for "{query}"
        </h2>
      </div>
      {showHint && (
        <div className="text-xs text-muted-foreground">
          Scoring: offer^4 • interview^3 • rejection^0.5 • {RECENCY_HINT} • Scale: {scale}
        </div>
      )}
    </div>
  );
}
