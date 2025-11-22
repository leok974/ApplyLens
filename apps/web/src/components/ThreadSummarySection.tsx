// Phase 5.2: Feedback collection for summary quality improvement.
// When user clicks Yes/No, we:
//  - POST to /api/actions/summary-feedback
//  - track analytics event (summary_feedback)
//  - show toast confirmation

import { ThreadSummary } from "@/types/thread";
import { cn } from "@/lib/utils";
import { useState, useCallback } from "react";
import { sendThreadSummaryFeedback } from "@/lib/api";
import { track } from "@/lib/analytics";
import { toast } from "sonner";

interface ThreadSummarySectionProps {
  summary: ThreadSummary | undefined;
  messageId: string | null; // <-- so we know what we're sending feedback about
}

export function ThreadSummarySection({ summary, messageId }: ThreadSummarySectionProps) {
  const [helpfulState, setHelpfulState] = useState<"yes" | "no" | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleFeedback = useCallback(
    async (val: "yes" | "no") => {
      if (!messageId) {
        // still update UI locally, but we can't send upstream
        setHelpfulState(val);
        return;
      }

      setHelpfulState(val);
      setSubmitting(true);

      // optimistic analytics
      track({
        name: "summary_feedback",
        messageId,
        helpful: val === "yes",
      });

      try {
        await sendThreadSummaryFeedback({
          messageId,
          helpful: val === "yes",
        });

        // small toast is optional, but we can do it for polish:
        toast.success(
          val === "yes" ? "Thanks for the feedback." : "We'll work on this."
        );
      } catch (err) {
        // we do NOT undo the UI state; miss is fine
        toast.error("Couldn't record feedback", {
          description: "Your response was not saved.",
        });
      } finally {
        setSubmitting(false);
      }
    },
    [messageId]
  );

  if (!summary) {
    return null;
  }

  return (
    <section
      data-testid="thread-summary-section"
      className={cn(
        "surface-panel border text-sm p-3 rounded-md space-y-2",
        "mt-4"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Summary
        </div>

        {/* Desktop-only feedback controls */}
        <div className="hidden sm:flex items-center gap-2 text-[11px] text-zinc-500 dark:text-zinc-400">
          {helpfulState === null ? (
            <div data-testid="summary-feedback-controls">
              <span className="text-[11px]">Helpful?</span>
              <button
                data-testid="summary-feedback-yes"
                disabled={submitting}
                onClick={() => handleFeedback("yes")}
                className={cn(
                  "px-1.5 py-0.5 rounded border text-[11px] font-medium ml-1",
                  "bg-emerald-100/70 text-emerald-700 border-emerald-400/40",
                  "dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-600/40",
                  "disabled:opacity-50"
                )}
              >
                Yes
              </button>
              <button
                data-testid="summary-feedback-no"
                disabled={submitting}
                onClick={() => handleFeedback("no")}
                className={cn(
                  "px-1.5 py-0.5 rounded border text-[11px] font-medium ml-1",
                  "bg-red-100/70 text-red-700 border-red-400/40",
                  "dark:bg-red-900/30 dark:text-red-300 dark:border-red-600/40",
                  "disabled:opacity-50"
                )}
              >
                No
              </button>
            </div>
          ) : (
            <span
              data-testid="summary-feedback-ack"
              className={cn(
                "text-[11px]",
                helpfulState === "yes"
                  ? "text-emerald-600 dark:text-emerald-300"
                  : "text-red-600 dark:text-red-300"
              )}
            >
              {helpfulState === "yes"
                ? "Thanks!"
                : "Got it — we'll improve this."}
            </span>
          )}
        </div>
      </div>

      {/* Headline */}
      {summary.headline && (
        <p data-testid="thread-summary-headline" className="text-[13px] font-medium text-zinc-900 dark:text-zinc-100">
          {summary.headline}
        </p>
      )}

      {/* Bullets */}
      {Array.isArray(summary.details) && summary.details.length > 0 && (
        <ul data-testid="thread-summary-details" className="list-disc pl-5 space-y-1 text-[13px] text-zinc-600 dark:text-zinc-300">
          {summary.details.map((d, idx) => (
            <li key={idx}>{d}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
