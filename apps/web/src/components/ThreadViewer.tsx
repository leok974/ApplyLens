import { useEffect, useState } from 'react';
import { X, ExternalLink, Shield, Archive, AlertTriangle, RefreshCw } from 'lucide-react';
import { fetchThreadDetail, fetchThreadAnalysis, MessageDetail } from '../lib/api';
import { ThreadRiskAnalysis } from '../types/thread';
import { ThreadViewerItem } from '../hooks/useThreadViewer';
import { safeFormatDate } from '../lib/date';
import { Badge } from './ui/badge';
import { cn } from '../lib/utils';
import { RiskAnalysisSection } from './RiskAnalysisSection';
import { ThreadActionBar } from './ThreadActionBar';
import { toast } from 'sonner';
import { track } from '../lib/analytics';
import { ThreadSummarySection } from './ThreadSummarySection';
import { ConversationTimelineSection } from './ConversationTimelineSection';

export interface ThreadViewerProps {
  emailId: string | null;
  isOpen: boolean;
  onClose: () => void;

  // NEW for Phase 3 navigation:
  goPrev: () => void;
  goNext: () => void;
  advanceAfterAction: () => void;

  // NEW for Phase 2.5 progress tracking:
  items?: ThreadViewerItem[];
  selectedIndex?: number | null;

  // NEW Phase 4 props
  autoAdvance: boolean;
  setAutoAdvance: (val: boolean) => void;

  handledCount: number;
  totalCount: number;

  bulkCount: number;
  onBulkArchive: () => void;
  onBulkMarkSafe: () => void;
  onBulkQuarantine: () => void;
  isBulkMutating?: boolean;

  onArchive?: (id: string) => void;
  onMarkSafe?: (id: string) => void;
  onQuarantine?: (id: string) => void;
}

export function ThreadViewer({
  emailId,
  isOpen,
  onClose,
  goPrev,
  goNext,
  advanceAfterAction,
  items = [],
  selectedIndex = null,
  autoAdvance,
  setAutoAdvance,
  handledCount,
  totalCount,
  bulkCount,
  onBulkArchive,
  onBulkMarkSafe,
  onBulkQuarantine,
  isBulkMutating = false,
  onArchive,
  onMarkSafe,
  onQuarantine,
}: ThreadViewerProps) {
  const [threadData, setThreadData] = useState<MessageDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Analysis state
  const [analysis, setAnalysis] = useState<ThreadRiskAnalysis | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Optimistic mutation state
  const [isMutating, setIsMutating] = useState(false);

  // TODO(thread-viewer v1.2):
  // Wire these actions to real backend endpoints:
  //  - POST /messages/:id/mark-safe
  //  - POST /messages/:id/quarantine
  //  - POST /messages/:id/archive
  // After mutation:
  //  - refresh list row state in parent list (Inbox/Search/Actions)
  //  - show toast confirmation
  //  - optionally auto-advance to next item

  async function handleMarkSafe() {
    if (!threadData) return;
    setIsMutating(true);
    try {
      // optimistic UI example: clear any 'quarantined' flag, maybe lower risk badge in UI
      setThreadData((prev) =>
        prev
          ? {
              ...prev,
              quarantined: false,
              // you can also imagine prev.status = "safe"
            }
          : prev
      );
      // await api.post(`/messages/${threadData.message_id}/mark-safe`)  <-- future
      toast.success('✅ Marked as safe', {
        description: 'Email marked as safe and removed from review queue'
      });
    } finally {
      setIsMutating(false);
    }
  }

  async function handleQuarantine() {
    if (!threadData) return;
    setIsMutating(true);
    try {
      // optimistic UI example: set quarantined true in local state
      setThreadData((prev) =>
        prev
          ? {
              ...prev,
              quarantined: true,
            }
          : prev
      );
      // await api.post(`/messages/${threadData.message_id}/quarantine`) <-- future
      toast.warning('🔒 Quarantined', {
        description: 'Email quarantined. Visible in Actions page.'
      });
    } finally {
      setIsMutating(false);
    }
  }

  async function handleArchive() {
    if (!threadData) return;
    setIsMutating(true);
    try {
      // optimistic UI: mark archived locally
      setThreadData((prev) =>
        prev
          ? {
              ...prev,
              archived: true,
            }
          : prev
      );
      // await api.post(`/messages/${threadData.message_id}/archive`) <-- future
      toast.success('📥 Archived and advanced', {
        description: 'Email archived successfully'
      });
    } finally {
      setIsMutating(false);
      // OPTIONAL NICE TOUCH:
      // after archiving, we could auto-close the drawer:
      // onClose();
    }
  }

  function handleOpenExternal() {
    if (!threadData) return;
    // assume threadData has something like gmailUrl or externalUrl from backend
    // fallback: no-op if it doesn't exist yet
    if ((threadData as any).externalUrl) {
      window.open((threadData as any).externalUrl, "_blank", "noopener,noreferrer");
    }
  }

  // Fetch thread data when opened with an emailId
  useEffect(() => {
    if (!isOpen || !emailId) {
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchThreadDetail(emailId)
      .then((data) => {
        if (!cancelled) {
          setThreadData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(String(err));
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, emailId]);

  // TODO(thread-viewer v1.1): Once backend supports thread-level analysis,
  // replace emailId with proper threadId. For now, we fetch analysis per emailId.
  // Fetch risk analysis after base thread data loads
  useEffect(() => {
    if (!isOpen || !emailId || loading || error) {
      return;
    }

    let cancelled = false;
    setAnalysisLoading(true);
    setAnalysisError(null);

    fetchThreadAnalysis(emailId)
      .then((data) => {
        if (!cancelled) {
          setAnalysis(data);
          setAnalysisLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setAnalysisError(String(err));
          setAnalysisLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, emailId, loading, error]);

  // TODO(thread-viewer v1.3):
  // Keyboard triage mode:
  //  - ArrowUp / ArrowDown navigate between threads
  //  - "D" archives current and advances
  // In the future we can add "Q" for quarantine and "S" for mark safe.
  // We intentionally do NOT close the drawer on navigation;
  // we just swap which thread is showing.
  useEffect(() => {
    if (!isOpen) return;

    function onKey(e: KeyboardEvent) {
      // Don't steal keys if user is typing in an input/textarea/select/contentEditable.
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.isContentEditable)
      ) {
        return;
      }

      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        goNext();
      } else if (e.key === "d" || e.key === "D") {
        e.preventDefault();
        // Phase 2 gave us handleArchive(); call that, then auto-advance.
        handleArchive();
        advanceAfterAction();
      }
    }

    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  }, [isOpen, onClose, goPrev, goNext, advanceAfterAction, handleArchive]);

  if (!isOpen) {
    return null;
  }

  return (
    <>
      {/* Backdrop - click to close on mobile */}
      <div
        className="fixed inset-0 bg-black/40 z-40 md:hidden"
        onClick={onClose}
      />

      {/* Drawer panel */}
      <aside
        data-testid="thread-viewer"
        className={cn(
          'fixed top-0 right-0 h-full w-full md:w-[480px] bg-card border-l border-border z-50',
          'flex flex-col shadow-2xl',
          'transition-transform duration-300 ease-out',
          isOpen ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Header */}
        <header className="flex items-start justify-between gap-3 p-4 border-b border-border bg-muted/30">
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-semibold text-foreground truncate">
              {loading ? 'Loading...' : threadData?.subject || 'Email Detail'}
            </h2>
            {threadData && (
              <>
                <p className="text-xs text-muted-foreground mt-1">
                  {safeFormatDate(threadData.received_at)}
                </p>
                {/* Progress counter */}
                {items.length > 0 && (
                  <p className="text-[10px] text-muted-foreground/70 mt-1 font-medium">
                    {items.filter(i => i.archived || i.quarantined).length} of {items.length} handled
                    {selectedIndex !== null && ` • ${selectedIndex + 1}/${items.length}`}
                  </p>
                )}
              </>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="p-6 text-center text-sm text-muted-foreground">
              <RefreshCw className="w-5 h-5 mx-auto mb-2 animate-spin" />
              Loading message...
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 text-sm text-destructive">
                <AlertTriangle className="w-4 h-4 inline mr-2" />
                {error}
              </div>
            </div>
          )}

          {!loading && !error && threadData && (
            <>
              {/* Meta information */}
              <div className="p-4 space-y-3 border-b border-border bg-background/50">
                <div className="text-xs space-y-1.5">
                  <div>
                    <span className="font-medium text-muted-foreground">From:</span>{' '}
                    <span className="text-foreground">
                      {threadData.from_name || threadData.from_email || 'Unknown'}
                    </span>
                    {threadData.from_email && threadData.from_name && (
                      <span className="text-muted-foreground ml-1">
                        &lt;{threadData.from_email}&gt;
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="font-medium text-muted-foreground">To:</span>{' '}
                    <span className="text-foreground">{threadData.to_email || 'You'}</span>
                  </div>
                </div>

                {/* Badges */}
                <div className="flex flex-wrap gap-2">
                  {threadData.category && (
                    <Badge variant="secondary" className="text-[10px]">
                      {threadData.category}
                    </Badge>
                  )}
                  {typeof threadData.risk_score === 'number' && (
                    <Badge
                      variant={threadData.risk_score > 70 ? 'destructive' : 'outline'}
                      className="text-[10px]"
                    >
                      Risk: {threadData.risk_score}
                    </Badge>
                  )}
                  {threadData.quarantined && (
                    <Badge variant="destructive" className="text-[10px]">
                      🔒 Quarantined
                    </Badge>
                  )}
                </div>

                {/* Risk Analysis Section */}
                <RiskAnalysisSection
                  loading={analysisLoading}
                  error={analysisError}
                  analysis={analysis}
                />

                {/* TODO(thread-viewer v1.5):
                    summary + timeline come from backend (or fallback mock in fetchThreadDetail()).
                    The goal is "I can understand this thread in 10 seconds.
                    I don't have to scroll 40 quoted replies to know what's happening." */}

                {/* Rolling summary of the conversation */}
                <ThreadSummarySection
                  summary={threadData?.summary}
                  messageId={emailId}
                />

                {/* Timeline of interaction */}
                <ConversationTimelineSection timeline={threadData?.timeline} />
              </div>

              {/* Message body */}
              <div className="p-4">
                {threadData.html_body ? (
                  <div
                    className="prose prose-sm dark:prose-invert max-w-none"
                    dangerouslySetInnerHTML={{ __html: threadData.html_body }}
                  />
                ) : threadData.text_body ? (
                  <pre className="whitespace-pre-wrap text-sm font-sans text-foreground bg-muted/10 p-3 rounded border border-border">
                    {threadData.text_body}
                  </pre>
                ) : (
                  <p className="text-sm text-muted-foreground italic">
                    No message content available.
                  </p>
                )}

                {/* Inline Action Bar */}
                {/* TODO(thread-viewer v1.4):
                     - handledCount, bulkCount, etc. will come from parent page state.
                       For now, parent can just stub them (0, items.length, selectedBulkIds.size).
                     - autoAdvance is user preference; we persist it in hook state.
                */}
                <ThreadActionBar
                  disabled={isMutating}
                  quarantined={Boolean(threadData?.quarantined)}
                  onMarkSafe={handleMarkSafe}
                  onQuarantine={handleQuarantine}
                  onArchive={handleArchive}
                  onOpenExternal={handleOpenExternal}
                  autoAdvance={autoAdvance}
                  onToggleAutoAdvance={() => {
                    const newValue = !autoAdvance;
                    setAutoAdvance(newValue);
                    track({ name: 'auto_advance_toggle', enabled: newValue });
                  }}
                  handledCount={handledCount}
                  totalCount={totalCount}
                  bulkCount={bulkCount}
                  onBulkArchive={onBulkArchive}
                  onBulkMarkSafe={onBulkMarkSafe}
                  onBulkQuarantine={onBulkQuarantine}
                  isBulkMutating={isBulkMutating}
                />
              </div>
            </>
          )}
        </div>

        {/* Footer actions */}
        {!loading && !error && threadData && (
          <footer className="p-4 border-t border-border bg-muted/30 flex flex-wrap gap-2">
            {onArchive && (
              <button
                onClick={() => onArchive(threadData.message_id)}
                className="px-3 py-1.5 text-xs rounded bg-muted hover:bg-muted/80 border border-border flex items-center gap-1.5 transition-colors"
              >
                <Archive className="w-3.5 h-3.5" />
                Archive
              </button>
            )}
            {onMarkSafe && (
              <button
                onClick={() => onMarkSafe(threadData.message_id)}
                className="px-3 py-1.5 text-xs rounded bg-emerald-600/20 text-emerald-200 border-emerald-700 hover:bg-emerald-600/30 border flex items-center gap-1.5 transition-colors"
              >
                <Shield className="w-3.5 h-3.5" />
                Mark Safe
              </button>
            )}
            {onQuarantine && !threadData.quarantined && (
              <button
                onClick={() => onQuarantine(threadData.message_id)}
                className="px-3 py-1.5 text-xs rounded bg-red-700/20 text-red-200 border-red-800 hover:bg-red-700/30 border flex items-center gap-1.5 transition-colors"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                Quarantine
              </button>
            )}
            {threadData.from_email && (
              <a
                href={`https://mail.google.com/mail/u/0/#search/from:${encodeURIComponent(threadData.from_email)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1.5 text-xs rounded bg-transparent border border-border hover:bg-muted/20 flex items-center gap-1.5 transition-colors ml-auto"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Open in Gmail
              </a>
            )}
          </footer>
        )}
      </aside>
    </>
  );
}
