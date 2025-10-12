import * as React from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { SenderAvatar } from "./SenderAvatar";
import { Archive, ShieldCheck, ShieldAlert, ExternalLink, ChevronRight } from "lucide-react";

const reasonStyle: Record<string, { label: string; className: string }> = {
  promo: { label: "Promo", className: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200" },
  bill:  { label: "Bill",  className: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200" },
  ats:   { label: "Application", className: "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200" },
  safe:  { label: "Safe",  className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200" },
  suspicious: { label: "Suspicious", className: "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200" },
};

type Props = {
  id: string;
  active?: boolean;
  checked?: boolean;
  onCheckChange?: (v: boolean) => void;

  subject: string;
  sender: string;                 // email or display
  preview: string;
  receivedAt: string;             // formatted
  reason?: keyof typeof reasonStyle;
  risk?: "low"|"med"|"high";

  density?: "compact"|"comfortable";

  onOpen?: () => void;
  onArchive?: () => void;
  onSafe?: () => void;
  onSus?: () => void;
  onExplain?: () => void;
};

export function EmailRow(props: Props) {
  const {
    active, checked, onCheckChange, subject, sender, preview, receivedAt, reason, risk, density="comfortable",
    onOpen, onArchive, onSafe, onSus, onExplain,
  } = props;

  const isCompact = density === "compact";

  return (
    <div
      onDoubleClick={onOpen}
      className={cn(
        "group relative flex w-full items-start gap-3 surface-card density-x density-y transition-colors",
        "hover:bg-[color:hsl(var(--muted))]/40",
        active && "ring-2 ring-[color:hsl(var(--ring))]/30",
      )}
      role="row"
    >
      {/* gradient accent on selection */}
      <div className={cn(
        "pointer-events-none absolute inset-x-0 top-0 h-1 rounded-t-xl",
        checked ? "bg-gradient-to-r from-indigo-500 via-fuchsia-500 to-pink-500" : "bg-transparent"
      )} />

      {/* left rail */}
      <div className="mt-0.5 grid place-items-center pl-1">
        <Checkbox checked={!!checked} onChange={(e) => onCheckChange?.((e.target as HTMLInputElement).checked)} />
      </div>

      <SenderAvatar from={sender} size={isCompact ? 28 : 32} />

      <div className="min-w-0 flex-1">
        <div className={cn("flex items-center gap-2", isCompact ? "text-[13px]" : "text-sm")}>
          <span className="truncate font-semibold text-[color:hsl(var(--foreground))]">{sender}</span>
          {reason && (
            <span className={cn(
              "rounded-full px-2 py-0.5 text-[11px] font-medium",
              reasonStyle[reason]?.className
            )}>{reasonStyle[reason]?.label ?? reason}</span>
          )}
          {risk === "high" && <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-semibold text-rose-800 dark:bg-rose-900/40 dark:text-rose-200">High risk</span>}
          <span className="ml-auto shrink-0 text-xs text-[color:hsl(var(--muted-foreground))]">{receivedAt}</span>
        </div>

        <div className={cn("mt-0.5 line-clamp-1 font-semibold leading-snug", isCompact ? "text-[14px]" : "text-base")}>
          {subject}
        </div>

        <div className={cn("mt-1 line-clamp-2 leading-relaxed prose-mail text-[color:hsl(var(--muted-foreground))]", isCompact ? "text-[12.5px]" : "text-[13px]")}>
          {preview}
        </div>
      </div>

      {/* hover actions */}
      <div className="ml-2 hidden shrink-0 items-center gap-1 group-hover:flex">
        <Button variant="ghost" size="icon" title="Archive" onClick={(e) => { e.stopPropagation(); onArchive?.(); }}>
          <Archive className="h-4 w-4 opacity-50 hover:opacity-100" />
        </Button>
        <Button variant="ghost" size="icon" title="Mark safe" onClick={(e) => { e.stopPropagation(); onSafe?.(); }}>
          <ShieldCheck className="h-4 w-4 opacity-50 hover:opacity-100" />
        </Button>
        <Button variant="ghost" size="icon" title="Mark suspicious" onClick={(e) => { e.stopPropagation(); onSus?.(); }}>
          <ShieldAlert className="h-4 w-4 opacity-50 hover:opacity-100" />
        </Button>
        <Button variant="ghost" size="icon" title="Explain why" onClick={(e) => { e.stopPropagation(); onExplain?.(); }}>
          <ExternalLink className="h-4 w-4 opacity-50 hover:opacity-100" />
        </Button>
        <ChevronRight className="ml-1 h-4 w-4 opacity-50" />
      </div>
    </div>
  );
}
