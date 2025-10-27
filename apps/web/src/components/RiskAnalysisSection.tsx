import { ThreadRiskAnalysis } from "@/types/thread";
import { cn } from "@/lib/utils";

interface RiskAnalysisSectionProps {
  loading: boolean;
  error: string | null;
  analysis: ThreadRiskAnalysis | null;
}

export function RiskAnalysisSection({
  loading,
  error,
  analysis,
}: RiskAnalysisSectionProps) {
  return (
    <section
      className={cn(
        "surface-panel border text-sm p-3 rounded-md space-y-2",
        // give it some visual identity
        "mt-4"
      )}
    >
      <div className="flex items-start justify-between">
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Analysis
        </div>
        {analysis?.riskLevel && (
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-medium border",
              analysis.riskLevel === "critical" &&
                "bg-red-500/20 text-red-200 border-red-400/60",
              analysis.riskLevel === "high" &&
                "bg-red-500/10 text-red-300 border-red-400/40",
              analysis.riskLevel === "medium" &&
                "bg-amber-500/10 text-amber-300 border-amber-400/40",
              analysis.riskLevel === "low" &&
                "bg-emerald-500/10 text-emerald-300 border-emerald-400/40"
            )}
          >
            {analysis.riskLevel.toUpperCase()}
          </span>
        )}
      </div>

      {loading && (
        <div className="text-zinc-500 dark:text-zinc-400 text-xs italic">
          Running analysis…
        </div>
      )}

      {error && !loading && (
        <div className="text-red-500 text-xs">
          {error}
        </div>
      )}

      {!loading && !error && analysis && (
        <>
          {analysis.summary && (
            <p className="text-zinc-800 dark:text-zinc-200 text-sm leading-relaxed">
              {analysis.summary}
            </p>
          )}

          {analysis.factors && analysis.factors.length > 0 && (
            <ul className="list-disc pl-4 text-[13px] text-zinc-700 dark:text-zinc-300 space-y-1">
              {analysis.factors.map((reason, idx) => (
                <li key={idx}>{reason}</li>
              ))}
            </ul>
          )}

          {analysis.recommendedAction && (
            <div className="text-[12px] text-zinc-500 dark:text-zinc-400">
              <span className="font-medium text-zinc-700 dark:text-zinc-200">
                Recommended:
              </span>{" "}
              {analysis.recommendedAction}
            </div>
          )}
        </>
      )}
    </section>
  );
}
