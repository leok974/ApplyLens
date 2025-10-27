// TODO(thread-viewer v1.5):
// The feedback buttons are local-only for now.
// Eventually we'll POST ("summary_helpful": true/false) so the model can learn
// what summaries/readouts humans trust.

import { ThreadSummary } from "@/types/thread";
import { cn } from "@/lib/utils";
import React from "react";

interface ThreadSummarySectionProps {
  summary: ThreadSummary | undefined;
}

export function ThreadSummarySection({ summary }: ThreadSummarySectionProps) {
  const [ack, setAck] = React.useState<null | "yes" | "no">(null);

  if (!summary) {
    return null;
  }

  return (
    <section
      className={cn(
        "surface-panel border text-sm p-3 rounded-md space-y-3",
        "mt-4"
      )}
    >
      <div className="flex items-start justify-between">
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Summary
        </div>
        {ack === null ? (
          <div className="flex items-center gap-2 text-[10px] text-zinc-500 dark:text-zinc-400">
            <span className="hidden sm:inline">Helpful?</span>
            <button
              className={cn(
                "rounded border px-1.5 py-0.5 leading-none font-medium",
                "bg-zinc-800/80 text-zinc-100 border-zinc-600/70",
                "hover:bg-zinc-700 hover:border-zinc-400/70",
                "text-[10px]"
              )}
              onClick={() => setAck("yes")}
            >
              Yes
            </button>
            <button
              className={cn(
                "rounded border px-1.5 py-0.5 leading-none font-medium",
                "bg-zinc-800/80 text-zinc-100 border-zinc-600/70",
                "hover:bg-zinc-700 hover:border-zinc-400/70",
                "text-[10px]"
              )}
              onClick={() => setAck("no")}
            >
              No
            </button>
          </div>
        ) : (
          <div className="text-[10px] text-zinc-500 dark:text-zinc-400">
            {ack === "yes" ? "Thanks!" : "Got it — we'll improve this."}
          </div>
        )}
      </div>

      {summary.headline && (
        <div className="text-zinc-800 dark:text-zinc-100 text-[13px] font-medium leading-normal">
          {summary.headline}
        </div>
      )}

      {summary.details && summary.details.length > 0 && (
        <ul className="list-disc pl-4 text-[13px] text-zinc-700 dark:text-zinc-300 space-y-1">
          {summary.details.map((d, idx) => (
            <li key={idx}>{d}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
