// TODO(thread-viewer v1.5):
// This timeline is designed for recruiter / security reviewer context:
// "What happened? When? Who owes the next move?"
// We will extend 'note' with model-generated intent labels ("asks for schedule", etc.).

import { ThreadTimelineEvent } from "@/types/thread";
import { cn } from "@/lib/utils";

interface ConversationTimelineSectionProps {
  timeline: ThreadTimelineEvent[] | undefined;
}

export function ConversationTimelineSection({ timeline }: ConversationTimelineSectionProps) {
  if (!timeline || timeline.length === 0) {
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
          Timeline
        </div>
      </div>

      <ol className="space-y-2 text-[13px] leading-relaxed">
        {timeline.map((evt, idx) => (
          <li
            key={idx}
            className={cn(
              "rounded-md border px-2 py-1.5",
              "border-zinc-300 bg-white text-zinc-800",
              "dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-200"
            )}
          >
            <div className="flex items-baseline justify-between">
              <div className="font-medium text-zinc-900 dark:text-zinc-100 text-[12px]">
                {evt.actor}
              </div>
              <div className="text-[11px] text-zinc-500 dark:text-zinc-400 tabular-nums">
                {new Date(evt.ts).toLocaleString()}
              </div>
            </div>

            <div className="text-[12px] text-zinc-600 dark:text-zinc-300">
              {evt.note}
            </div>

            {evt.kind && (
              <div
                className={cn(
                  "mt-1 inline-block rounded px-1.5 py-0.5 text-[10px] font-medium border",
                  evt.kind === "flagged" &&
                    "bg-red-600/20 text-red-200 border-red-400/60",
                  evt.kind === "follow_up_needed" &&
                    "bg-amber-500/20 text-amber-100 border-amber-400/60",
                  (evt.kind === "replied" || evt.kind === "received") &&
                    "bg-zinc-800/60 text-zinc-200 border-zinc-500/60",
                  evt.kind === "status_change" &&
                    "bg-blue-600/20 text-blue-200 border-blue-400/60"
                )}
              >
                {evt.kind.replace(/_/g, " ")}
              </div>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
