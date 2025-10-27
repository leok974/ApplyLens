import { useEffect, useState } from 'react';
import { X, ExternalLink, Shield, Archive, AlertTriangle, RefreshCw } from 'lucide-react';
import { fetchThreadDetail, MessageDetail } from '../lib/api';
import { safeFormatDate } from '../lib/date';
import { Badge } from './ui/badge';
import { cn } from '../lib/utils';

export interface ThreadViewerProps {
  emailId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onArchive?: (id: string) => void;
  onMarkSafe?: (id: string) => void;
  onQuarantine?: (id: string) => void;
}

export function ThreadViewer({
  emailId,
  isOpen,
  onClose,
  onArchive,
  onMarkSafe,
  onQuarantine,
}: ThreadViewerProps) {
  const [threadData, setThreadData] = useState<MessageDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  // Handle Escape key to close
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

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
              <p className="text-xs text-muted-foreground mt-1">
                {safeFormatDate(threadData.received_at)}
              </p>
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
