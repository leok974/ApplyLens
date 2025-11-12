import { cn } from "@/lib/utils";

interface ThreadActionBarProps {
  disabled?: boolean;
  quarantined?: boolean;
  onMarkSafe: () => void;
  onQuarantine: () => void;
  onArchive: () => void;
  onOpenExternal: () => void;

  // NEW Phase 4:
  autoAdvance: boolean;
  onToggleAutoAdvance: () => void;

  handledCount: number;
  totalCount: number;

  bulkCount: number;
  onBulkArchive: () => void;
  onBulkMarkSafe: () => void;
  onBulkQuarantine: () => void;
  isBulkMutating?: boolean;
}

export function ThreadActionBar({
  disabled,
  quarantined,
  onMarkSafe,
  onQuarantine,
  onArchive,
  onOpenExternal,
  autoAdvance,
  onToggleAutoAdvance,
  handledCount,
  totalCount,
  bulkCount,
  onBulkArchive,
  onBulkMarkSafe,
  onBulkQuarantine,
  isBulkMutating = false,
}: ThreadActionBarProps) {
  // TODO(thread-viewer v1.4):
  // - handledCount should come from parent list state (archived/quarantined/etc)
  // - bulk buttons show only when multiple are selected
  // - auto-advance toggle controls advanceAfterAction() behavior
  return (
    <div
      data-testid="thread-action-bar"
      className={cn(
        "border-t mt-4 pt-3 flex flex-col gap-3 text-sm",
        "sm:flex-row sm:items-start sm:justify-between"
      )}
    >
      {/* Left side: action buttons */}
      <div className="flex flex-wrap gap-2">
        {bulkCount > 1 ? (
          <>
            <button
              data-testid="action-archive-bulk"
              className={cn(
                "rounded-md border px-2.5 py-1 text-[11px] font-medium",
                "bg-zinc-800/80 border-zinc-600/70 text-zinc-100",
                "hover:bg-zinc-700 hover:border-zinc-400/70",
                "disabled:opacity-40 disabled:cursor-not-allowed"
              )}
              disabled={disabled || isBulkMutating}
              onClick={onBulkArchive}
            >
              {isBulkMutating ? "Processing..." : `Archive ${bulkCount} selected`}
            </button>

            <button
              data-testid="action-mark-safe-bulk"
              className={cn(
                "rounded-md border px-2.5 py-1 text-[11px] font-medium",
                "bg-emerald-600/20 text-emerald-200 border-emerald-400/60 hover:bg-emerald-600/30",
                "disabled:opacity-40 disabled:cursor-not-allowed"
              )}
              disabled={disabled || isBulkMutating}
              onClick={onBulkMarkSafe}
            >
              {isBulkMutating ? "Processing..." : `Mark Safe (${bulkCount})`}
            </button>

            <button
              data-testid="action-quarantine-bulk"
              className={cn(
                "rounded-md border px-2.5 py-1 text-[11px] font-medium",
                "bg-red-600/20 text-red-200 border-red-400/60 hover:bg-red-600/30",
                "disabled:opacity-40 disabled:cursor-not-allowed"
              )}
              disabled={disabled || isBulkMutating}
              onClick={onBulkQuarantine}
            >
              {isBulkMutating ? "Processing..." : `Quarantine ${bulkCount}`}
            </button>
          </>
        ) : (
          <>
            <button
              data-testid="action-mark-safe-single"
              className={cn(
                "rounded-md border px-2.5 py-1 text-xs font-medium",
                "bg-zinc-800/80 border-zinc-600/70 text-zinc-100",
                "hover:bg-zinc-700 hover:border-zinc-400/70",
                "disabled:opacity-40 disabled:cursor-not-allowed"
              )}
              disabled={disabled}
              onClick={onMarkSafe}
            >
              Mark Safe
            </button>

            <button
              data-testid="action-quarantine-single"
              className={cn(
                "rounded-md border px-2.5 py-1 text-xs font-medium",
                quarantined
                  ? "bg-red-900/20 text-red-300 border-red-400/40"
                  : "bg-red-600/20 text-red-200 border-red-400/60 hover:bg-red-600/30",
                "disabled:opacity-40 disabled:cursor-not-allowed"
              )}
              disabled={disabled}
              onClick={onQuarantine}
            >
              {quarantined ? "Quarantined" : "Quarantine"}
            </button>

            <button
              data-testid="action-archive-single"
              className={cn(
                "rounded-md border px-2.5 py-1 text-xs font-medium",
                "bg-zinc-800/80 border-zinc-600/70 text-zinc-100",
                "hover:bg-zinc-700 hover:border-zinc-400/70",
                "disabled:opacity-40 disabled:cursor-not-allowed"
              )}
              disabled={disabled}
              onClick={onArchive}
            >
              Archive
            </button>

            <button
              data-testid="action-open-gmail"
              className={cn(
                "rounded-md border px-2.5 py-1 text-xs font-medium",
                "bg-zinc-800/80 border-zinc-600/70 text-zinc-100",
                "hover:bg-zinc-700 hover:border-zinc-400/70",
                "disabled:opacity-40 disabled:cursor-not-allowed"
              )}
              disabled={disabled}
              onClick={onOpenExternal}
            >
              Open in Gmail →
            </button>
          </>
        )}
      </div>

      {/* Right side: status + prefs */}
      <div className="flex flex-col items-start gap-2 text-[11px] text-zinc-400 dark:text-zinc-500 sm:items-end sm:text-right">
        <div data-testid="handled-progress" className="text-[11px] leading-none">
          {handledCount} of {totalCount} handled
        </div>

        <label
          data-testid="auto-advance-toggle"
          className={cn(
            "flex items-center gap-1 rounded border px-2 py-1 text-[10px] font-medium cursor-pointer",
            autoAdvance
              ? "bg-zinc-800/80 text-zinc-100 border-zinc-600/70"
              : "bg-transparent text-zinc-400 border-zinc-700/60",
            "hover:bg-zinc-700 hover:text-zinc-100 hover:border-zinc-500/70"
          )}
        >
          <input
            type="checkbox"
            className="sr-only"
            checked={autoAdvance}
            onChange={onToggleAutoAdvance}
            disabled={disabled}
          />
          <span
            className={cn(
              "inline-block w-2 h-2 rounded-sm border",
              autoAdvance
                ? "bg-emerald-400 border-emerald-300"
                : "bg-transparent border-zinc-500"
            )}
          />
          <span>Auto-advance</span>
        </label>
      </div>
    </div>
  );
}
