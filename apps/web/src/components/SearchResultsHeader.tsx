import { RECENCY_HINT } from "../lib/searchScoring";
import { getRecencyScale } from "../state/searchPrefs";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Info } from "lucide-react";

type Props = { query: string; total?: number; showHint?: boolean; debugScore?: boolean };

export default function SearchResultsHeader({ query, total, showHint, debugScore }: Props) {
  const scale = getRecencyScale();

  return (
    <div className="mb-3 flex items-center justify-between" data-testid="results-header">
      <div className="text-sm">
        <h2
          className="inline"
          aria-live="polite"
          aria-atomic="true"
        >
          <span className="text-muted-foreground">Results</span>{" "}
          <span className="font-medium">{typeof total === "number" ? total : "—"}</span>
          <span className="text-muted-foreground"> for </span>
          <span className="italic">"{query || "*"}"</span>
        </h2>
      </div>

      {showHint && (
        <div className="flex items-center gap-2">
          {debugScore && (
            <Badge
              variant="outline"
              className="gap-1 text-[10px] font-mono text-yellow-600 dark:text-yellow-400 bg-yellow-500/10 border-yellow-500/30"
            >
              debugScore ON
            </Badge>
          )}

          <Tooltip>
            <TooltipTrigger asChild>
              <Badge
                variant="outline"
                className="gap-1 cursor-help"
                data-testid="scoring-pill"
              >
                <Info className="h-3 w-3" />
                Scoring
              </Badge>
            </TooltipTrigger>
            <TooltipContent className="max-w-[340px] text-xs">
              <div className="space-y-1">
                <div><span className="font-medium">Boosts:</span> offer ×4, interview ×3, rejection ×0.5</div>
                <div><span className="font-medium">Recency:</span> {RECENCY_HINT}</div>
                <div><span className="font-medium">Time scale:</span> {scale}</div>
              </div>
            </TooltipContent>
          </Tooltip>
        </div>
      )}
    </div>
  );
}
