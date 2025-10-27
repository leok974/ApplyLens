import { cn } from "@/lib/utils";

interface ThreadActionBarProps {
  disabled?: boolean;
  quarantined?: boolean;
  onMarkSafe: () => void;
  onQuarantine: () => void;
  onArchive: () => void;
  onOpenExternal: () => void;
}

export function ThreadActionBar({
  disabled,
  quarantined,
  onMarkSafe,
  onQuarantine,
  onArchive,
  onOpenExternal,
}: ThreadActionBarProps) {
  return (
    <div
      className={cn(
        "border-t mt-4 pt-3 flex flex-wrap gap-2 justify-between",
        // live inside ThreadViewer, so match its surface
        "text-sm"
      )}
    >
      <div className="flex flex-wrap gap-2">
        <button
          className={cn(
            "rounded-md border px-2.5 py-1 text-xs font-medium",
            "bg-zinc-800/80 border-zinc-600/70 text-zinc-100",
            "hover:bg-zinc-700 hover:border-zinc-400/70",
            "disabled:opacity-40 disabled:cursor-not-allowed",
            "dark:bg-zinc-800/80 dark:text-zinc-100 dark:border-zinc-600/70",
            "dark:hover:bg-zinc-700"
          )}
          disabled={disabled}
          onClick={onMarkSafe}
        >
          Mark Safe
        </button>

        <button
          className={cn(
            "rounded-md border px-2.5 py-1 text-xs font-medium",
            quarantined
              ? // already quarantined → softer style
                "bg-red-900/20 text-red-300 border-red-400/40"
              : // not quarantined yet → stronger CTA
                "bg-red-600/20 text-red-200 border-red-400/60 hover:bg-red-600/30",
            "disabled:opacity-40 disabled:cursor-not-allowed"
          )}
          disabled={disabled}
          onClick={onQuarantine}
        >
          {quarantined ? "Quarantined" : "Quarantine"}
        </button>

        <button
          className={cn(
            "rounded-md border px-2.5 py-1 text-xs font-medium",
            "bg-zinc-800/80 border-zinc-600/70 text-zinc-100",
            "hover:bg-zinc-700 hover:border-zinc-400/70",
            "disabled:opacity-40 disabled:cursor-not-allowed",
            "dark:bg-zinc-800/80 dark:text-zinc-100 dark:border-zinc-600/70",
            "dark:hover:bg-zinc-700"
          )}
          disabled={disabled}
          onClick={onArchive}
        >
          Archive
        </button>
      </div>

      <button
        className={cn(
          "rounded-md border px-2.5 py-1 text-xs font-medium",
          "bg-zinc-800/80 border-zinc-600/70 text-zinc-100",
          "hover:bg-zinc-700 hover:border-zinc-400/70",
          "disabled:opacity-40 disabled:cursor-not-allowed",
          "dark:bg-zinc-800/80 dark:text-zinc-100 dark:border-zinc-600/70",
          "dark:hover:bg-zinc-700"
        )}
        disabled={disabled}
        onClick={onOpenExternal}
      >
        Open in Gmail →
      </button>
    </div>
  );
}
