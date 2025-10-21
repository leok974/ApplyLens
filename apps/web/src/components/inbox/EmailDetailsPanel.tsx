import * as React from "react";
import {
  X, ExternalLink, ShieldAlert, ShieldCheck, Archive, Loader2,
  ChevronLeft, ChevronRight, GripVertical
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SecurityPanel } from "@/components/security/SecurityPanel";
import { RiskFlag } from "@/types/security";
import {
  EmailRiskBanner,
  fetchEmailRiskAdvice,
  type EmailRiskAdvice,
  generateVerificationEmailDraft
} from "@/components/email/EmailRiskBanner";

export type EmailDetails = {
  id: string;
  subject: string;
  from: string;
  to?: string;
  date: string;
  labels?: string[];
  risk?: "low"|"med"|"high";
  reason?: string;
  body_html?: string;
  body_text?: string;
  thread_id?: string;
  unsubscribe_url?: string | null;
  // Security fields
  risk_score?: number;
  quarantined?: boolean;
  flags?: RiskFlag[];
};

type ThreadItem = {
  id: string;
  from: string;
  date: string;           // pretty date
  snippet?: string;
  body_html?: string;
  body_text?: string;
};

type PanelMode = "overlay" | "split";

const LS_KEY = "inbox:detailsPanelWidth";

export function EmailDetailsPanel({
  open,
  mode = "overlay",
  onClose,
  loading,
  email,
  thread,
  indexInThread,
  onPrev,
  onNext,
  onJump,         // optional quick jump by index
  onArchive,
  onMarkSafe,
  onMarkSus,
  onExplain,
}: {
  open: boolean;
  mode?: PanelMode;
  onClose: () => void;
  loading?: boolean;
  email?: EmailDetails | null;
  thread?: ThreadItem[];        // ordered oldest..newest
  indexInThread?: number | null;
  onPrev?: () => void;
  onNext?: () => void;
  onJump?: (i:number) => void;

  onArchive?: () => void;
  onMarkSafe?: () => void;
  onMarkSus?: () => void;
  onExplain?: () => void;
}) {
  // Risk advice state
  const [riskAdvice, setRiskAdvice] = React.useState<EmailRiskAdvice | null>(null);
  const [loadingRisk, setLoadingRisk] = React.useState(false);

  // Fetch risk advice when email changes
  React.useEffect(() => {
    if (!email?.id) {
      setRiskAdvice(null);
      return;
    }

    setLoadingRisk(true);
    fetchEmailRiskAdvice(email.id)
      .then((advice) => setRiskAdvice(advice))
      .catch((err) => console.error("Failed to load risk advice:", err))
      .finally(() => setLoadingRisk(false));
  }, [email?.id]);

  // Handler for "Mark as Scam" button
  const handleMarkScam = React.useCallback(() => {
    if (!email) return;
    // Call parent handler if provided
    onMarkSus?.();
    // TODO: Also add "scam" or "suspicious" label via API
    console.log(`Marking email ${email.id} as scam`);
  }, [email, onMarkSus]);

  // Handler for "Request Official Invite" button
  const handleRequestOfficial = React.useCallback(() => {
    if (!email) return;

    // Extract recruiter name from "from" field
    const fromMatch = email.from.match(/^([^<]+)/);
    const recruiterName = fromMatch ? fromMatch[1].trim() : "Recruiter";

    // Generate draft email
    const draft = generateVerificationEmailDraft(recruiterName, "[Your Name]");

    // Copy to clipboard
    navigator.clipboard.writeText(draft).then(() => {
      alert("Verification email template copied to clipboard! Open your email client to send.");
    }).catch((err) => {
      console.error("Failed to copy to clipboard:", err);
      // Fallback: open mailto link
      const subject = encodeURIComponent("Verification before scheduling");
      const body = encodeURIComponent(draft.split('\n\n').slice(1).join('\n\n'));
      window.open(`mailto:${email.from}?subject=${subject}&body=${body}`);
    });
  }, [email]);

  // width state + persistence
  const [width, setWidth] = React.useState<number>(() => {
    const saved = Number(localStorage.getItem(LS_KEY));
    return Number.isFinite(saved) && saved >= 420 && saved <= 1000 ? saved : 720;
  });

  const startDrag = React.useRef<{x:number; w:number} | null>(null);
  const onPointerDown = (e: React.PointerEvent) => {
    startDrag.current = { x: e.clientX, w: width };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!startDrag.current) return;
    const dx = startDrag.current.x - e.clientX; // dragging left increases width
    const next = Math.min(1000, Math.max(420, startDrag.current.w + dx));
    setWidth(next);
  };
  const onPointerUp = () => {
    if (startDrag.current) {
      localStorage.setItem(LS_KEY, String(width));
      startDrag.current = null;
    }
  };

  // Esc to close
  React.useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "[" && onPrev) onPrev();
      if (e.key === "]" && onNext) onNext();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose, onPrev, onNext]);

  const body = (e?: {body_html?:string; body_text?:string}) => {
    if (!e) return null;
    if (e.body_html)
      return (
        <article
          className="prose prose-slate max-w-none dark:prose-invert
                     prose-a:text-[hsl(var(--accent))] dark:prose-a:text-[hsl(var(--accent))]"
          dangerouslySetInnerHTML={{ __html: e.body_html }}
        />
      );
    return (
      <pre className="whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm text-slate-700 dark:bg-slate-900 dark:text-slate-200">
        {e.body_text || "(No body content)"}
      </pre>
    );
  };

  // container classes differ by mode
  const containerClass =
    mode === "overlay"
      ? cn(
          "fixed inset-y-0 right-0 z-40 transform bg-card text-card-foreground shadow-2xl transition-transform",
          open ? "translate-x-0" : "translate-x-full"
        )
      : cn(
          // split mode: static block that fills parent height
          "relative z-0 bg-card text-card-foreground border-l border-[color:hsl(var(--color-border))] h-full"
        );

  return (
    <div
      data-testid="email-details-panel"
      className={containerClass}
      style={{ width }}
      role="dialog"
      aria-modal="true"
    >
      {/* Drag handle */}
      <div
        data-testid="details-resizer"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        className="absolute left-0 top-0 z-50 h-full w-2 cursor-col-resize"
        aria-label="Resize panel"
      >
        <div className="absolute left-[-6px] top-1/2 -translate-y-1/2 rounded-full border border-[color:hsl(var(--color-border))] bg-[color:hsl(var(--color-muted))] px-1 py-1 opacity-70 hover:opacity-100">
          <GripVertical className="h-3.5 w-3.5 text-slate-400" />
        </div>
      </div>

      {/* Header */}
      <div className="flex h-14 items-center gap-2 border-b border-[color:hsl(var(--color-border))] px-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          aria-label="Close"
          className={mode === "split" ? "md:hidden" : ""}
        >
          <X className="h-5 w-5" />
        </Button>

        {/* Thread nav */}
        <div className="ml-1 flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={onPrev} disabled={!onPrev}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={onNext} disabled={!onNext}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          {typeof indexInThread === "number" && thread?.length ? (
            <span className="ml-1 text-xs text-slate-500" data-testid="thread-indicator">
              {indexInThread + 1} / {thread.length}
            </span>
          ) : null}
        </div>

        <div className="ml-auto flex items-center gap-1">
          <Button variant="ghost" size="icon" title="Archive" onClick={onArchive}>
            <Archive className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" title="Mark safe" onClick={onMarkSafe}>
            <ShieldCheck className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" title="Mark suspicious" onClick={onMarkSus}>
            <ShieldAlert className="h-4 w-4" />
          </Button>
          <Button variant="secondary" size="sm" onClick={onExplain}>
            Explain why
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="grid h-[calc(100%-56px)] place-items-center">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      ) : !email ? (
        <div className="grid h-[calc(100%-56px)] place-items-center text-sm text-slate-500">
          Select an email to view details
        </div>
      ) : (
        <ScrollArea className="h-[calc(100%-56px)]">
          <div className="space-y-4 p-6">
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
                {email.subject}
              </h1>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span>From: <span className="font-medium text-slate-700 dark:text-slate-300">{email.from}</span></span>
                {email.to && <span>• To: {email.to}</span>}
                <span>• {email.date}</span>
                {email.labels?.length ? (
                  <>
                    <span>•</span>
                    {email.labels.slice(0,5).map((l) => (
                      <Badge key={l} variant="outline" className="border-[color:hsl(var(--color-border))] text-slate-600 dark:text-slate-300">{l}</Badge>
                    ))}
                    {email.labels.length > 5 && <span className="text-slate-400">+{email.labels.length - 5}</span>}
                  </>
                ) : null}
                {email.reason && (
                  <>
                    <span>•</span>
                    <Badge className="bg-[color:hsl(var(--color-accent))] text-[color:hsl(var(--color-accent-foreground))]">Reason: {email.reason}</Badge>
                  </>
                )}
                {email.risk === "high" && <Badge className="bg-rose-600 text-white">High risk</Badge>}
              </div>
            </div>

            <Separator />

            {/* Risk banner (v3 phishing detection) */}
            {!loadingRisk && riskAdvice && (
              <>
                <EmailRiskBanner
                  emailId={email.id}
                  riskAdvice={riskAdvice}
                  onMarkScam={handleMarkScam}
                  onRequestOfficial={handleRequestOfficial}
                />
                <Separator />
              </>
            )}

            {/* Security panel */}
            {email.risk_score !== undefined && (
              <>
                <SecurityPanel
                  emailId={email.id}
                  riskScore={email.risk_score ?? 0}
                  quarantined={email.quarantined}
                  flags={email.flags}
                  onRefresh={() => {
                    // Parent can implement refresh logic
                    console.log('Security panel refresh requested');
                  }}
                />
                <Separator />
              </>
            )}

            {/* Current message body */}
            {body(email)}

            {email.unsubscribe_url && (
              <div className="mt-6">
                <a className="inline-flex items-center gap-1 text-sm font-medium underline"
                   href={email.unsubscribe_url} target="_blank" rel="noreferrer">
                  Unsubscribe <ExternalLink className="h-4 w-4" />
                </a>
              </div>
            )}

            {/* Thread list */}
            {thread && thread.length > 1 && (
              <>
                <Separator />
                <div className="text-xs font-medium text-slate-500">Thread</div>
                <div className="mt-2 space-y-2">
                  {thread.map((m, i) => (
                    <button
                      key={m.id}
                      onClick={() => onJump?.(i)}
                      className={cn(
                        "w-full rounded-lg border p-3 text-left transition-colors",
                        "border-[color:hsl(var(--color-border))] hover:bg-[color:hsl(var(--color-muted))]/60",
                        i === indexInThread && "bg-[color:hsl(var(--color-muted))]/70"
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <div className="truncate text-sm font-medium">{m.from}</div>
                        <div className="ml-2 shrink-0 text-[11px] text-slate-500">{m.date}</div>
                      </div>
                      {m.snippet && (
                        <div className="mt-1 line-clamp-2 text-xs text-slate-500">{m.snippet}</div>
                      )}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </ScrollArea>
      )}
    </div>
  );
}
