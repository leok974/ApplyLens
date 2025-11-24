import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import type { MailThreadSummary, MailThreadDetail, MailMessage } from '@/lib/mailThreads';
import { formatDistanceToNow, format } from 'date-fns';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ExternalLink, Check, AlertTriangle, Copy, Clock, Plus, Briefcase, Sparkles } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { useFollowupDraft } from '@/hooks/useFollowupDraft';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface ThreadViewerProps {
  threadId: string | null;
  summary: MailThreadSummary | null;
  onCreateApplication?: (threadId: string) => void;
  intent?: string; // Current intent (e.g., 'followups', 'bills') for observability
}

export function ThreadViewer({ threadId, summary, onCreateApplication, intent }: ThreadViewerProps) {
  const navigate = useNavigate();
  const [detail, setDetail] = useState<MailThreadDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Follow-up draft generation
  const { draft, isGenerating, generateDraft, clearDraft, copyDraftToClipboard, copyBodyToClipboard } = useFollowupDraft();

  useEffect(() => {
    if (!threadId) {
      setDetail(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`/api/threads/${threadId}`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = (await res.json()) as MailThreadDetail;
        if (!cancelled) setDetail(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load thread');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [threadId]);

  if (!threadId || !summary) {
    return (
      <div
        className="rounded-lg border border-slate-800/50 bg-slate-950/30 p-6 text-center"
        data-testid="thread-viewer-empty"
      >
        <p className="text-sm text-slate-400">Select a thread to view details</p>
      </div>
    );
  }

  // Normalize detail and messages for null-safety
  const safeDetail = detail ?? (summary as MailThreadDetail);
  const messages = safeDetail?.messages ?? [];

  const isRisky = (summary.riskScore ?? 0) > 0.7;

  return (
    <div
      className="rounded-lg border border-slate-800/50 bg-slate-950/30 p-4"
      data-testid="thread-viewer"
    >
      {/* Header */}
      <div className="mb-4 border-b border-slate-800/50 pb-4">
        <div className="flex items-start justify-between gap-3 mb-2">
          <h3 className="text-base font-semibold text-slate-100">{summary.subject}</h3>
          <div className="flex items-center gap-2 shrink-0">
            {isRisky && (
              <Badge variant="destructive" className="shrink-0">
                <AlertTriangle className="mr-1 h-3 w-3" />
                Risky
              </Badge>
            )}
            {summary.applicationId && (
              <Badge
                variant="outline"
                className="shrink-0 border-yellow-400/30 text-yellow-400"
                data-testid="thread-viewer-app-badge"
              >
                <Briefcase className="mr-1 h-3 w-3" />
                Application linked
              </Badge>
            )}
          </div>
        </div>

        <div className="space-y-1 text-sm text-slate-400">
          <div>
            <span className="font-medium">From:</span> {summary.from}
            {summary.to && (
              <>
                {' → '}
                <span className="font-medium">To:</span> {summary.to}
              </>
            )}
          </div>
          <div>
            <span className="font-medium">Received:</span>{' '}
            {format(new Date(summary.lastMessageAt), 'PPp')}
          </div>
        </div>

        {summary.labels.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {summary.labels.map((label) => (
              <span
                key={label}
                className="inline-block rounded bg-slate-800/50 px-2 py-0.5 text-xs text-slate-300"
              >
                {label}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="mb-4 flex flex-wrap gap-2">
        <Button
          variant="default"
          size="sm"
          asChild
          className="bg-yellow-500/90 hover:bg-yellow-500 text-slate-950"
        >
          <a href={summary.gmailUrl} target="_blank" rel="noopener noreferrer">
            <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
            Open in Gmail
          </a>
        </Button>

        {/* Application action */}
        {summary.applicationId ? (
          <Button
            variant="outline"
            size="sm"
            className="border-yellow-400/30 text-yellow-400 hover:bg-yellow-400/10"
            onClick={() => {
              // Track thread-to-tracker click for observability (fire-and-forget)
              fetch('/metrics/thread-to-tracker-click', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  application_id: summary.applicationId,
                  intent: intent ?? undefined,
                }),
              }).catch(() => {
                // Swallow errors – don't block navigation
              });

              // Navigate to tracker
              navigate(`/tracker?appId=${summary.applicationId}`);
            }}
            data-testid="thread-viewer-open-tracker"
          >
            <Briefcase className="mr-1.5 h-3.5 w-3.5" />
            Open in Tracker
          </Button>
        ) : onCreateApplication && (
          <Button
            variant="outline"
            size="sm"
            className="border-slate-700 text-slate-300"
            onClick={() => onCreateApplication(threadId!)}
            data-testid="thread-viewer-create-app"
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Create application
          </Button>
        )}

        <Button variant="outline" size="sm" className="border-slate-700 text-slate-300">
          <Check className="mr-1.5 h-3.5 w-3.5" />
          Mark Handled
        </Button>

        {isRisky && (
          <Button variant="outline" size="sm" className="border-slate-700 text-slate-300">
            <AlertTriangle className="mr-1.5 h-3.5 w-3.5" />
            Mark as Safe
          </Button>
        )}

        <Button
          variant="ghost"
          size="sm"
          className="text-slate-400"
          onClick={() => {
            navigator.clipboard.writeText(summary.snippet);
          }}
        >
          <Copy className="mr-1.5 h-3.5 w-3.5" />
          Copy Summary
        </Button>

        {/* Follow-up Draft */}
        <Button
          variant="outline"
          size="sm"
          className="border-purple-500/30 text-purple-400 hover:bg-purple-500/10"
          onClick={() => {
            if (threadId) {
              generateDraft({
                threadId,
                applicationId: summary.applicationId ?? undefined,
              });
            }
          }}
          disabled={isGenerating}
          data-testid="thread-viewer-draft-followup"
        >
          <Sparkles className="mr-1.5 h-3.5 w-3.5" />
          {isGenerating ? 'Generating...' : 'Draft follow-up'}
        </Button>
      </div>

      {/* Follow-up Draft Display */}
      {draft && (
        <div className="mb-4">
          <Card className="border-purple-500/30 bg-purple-950/20">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-base text-purple-100">Follow-up Draft</CardTitle>
                  <CardDescription className="text-purple-300/70">
                    AI-generated follow-up email
                  </CardDescription>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearDraft}
                  className="text-purple-400 hover:text-purple-300 -mt-1 -mr-2"
                >
                  ✕
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Subject */}
              <div>
                <div className="text-xs font-medium text-purple-300/70 mb-1">Subject:</div>
                <div className="text-sm text-purple-100 font-medium bg-purple-900/20 rounded px-3 py-2">
                  {draft.subject}
                </div>
              </div>

              {/* Body */}
              <div>
                <div className="text-xs font-medium text-purple-300/70 mb-1">Body:</div>
                <div className="text-sm text-purple-100 whitespace-pre-wrap bg-purple-900/20 rounded px-3 py-2.5 max-h-64 overflow-y-auto">
                  {draft.body}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-1">
                <Button
                  size="sm"
                  className="bg-purple-500/90 hover:bg-purple-500 text-white"
                  onClick={copyDraftToClipboard}
                >
                  <Copy className="mr-1.5 h-3 w-3" />
                  Copy Full Draft
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="border-purple-500/30 text-purple-400 hover:bg-purple-500/10"
                  onClick={copyBodyToClipboard}
                >
                  <Copy className="mr-1.5 h-3 w-3" />
                  Copy Body Only
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Message Timeline */}
      <div>
        <h4 className="mb-3 text-sm font-medium text-slate-300">Message Timeline</h4>

        {loading && !detail && (
          <div className="space-y-3" data-testid="thread-viewer-loading">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-4 w-3/4 bg-slate-800/50" />
                <Skeleton className="h-3 w-1/2 bg-slate-800/30" />
                <Skeleton className="h-16 w-full bg-slate-800/20" />
              </div>
            ))}
          </div>
        )}

        {error && !detail && (
          <div
            className="rounded-lg border border-red-900/50 bg-red-950/30 p-3 text-sm text-red-400"
            data-testid="thread-viewer-error"
          >
            {error}
          </div>
        )}

        {messages.length === 0 && !loading && !error ? (
          <p className="text-sm text-slate-500">No messages found in this thread yet.</p>
        ) : (
          <div className="space-y-3">
            {messages.map((message, index) => (
              <MessageCard key={message.id} message={message} isFirst={index === 0} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MessageCard({ message, isFirst }: { message: MailMessage; isFirst: boolean }) {
  const [expanded, setExpanded] = useState(isFirst);

  return (
    <div
      className={cn(
        'rounded-lg border border-slate-800/50 bg-slate-900/30 p-3',
        message.isImportant && 'border-yellow-400/20'
      )}
      data-testid="message-card"
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-slate-200 truncate">{message.from}</span>
            {message.isImportant && (
              <Badge variant="outline" className="text-xs border-yellow-400/30 text-yellow-400">
                Important
              </Badge>
            )}
          </div>
          <div className="text-xs text-slate-400">
            <Clock className="mr-1 inline h-3 w-3" />
            {formatDistanceToNow(new Date(message.sentAt), { addSuffix: true })} •{' '}
            {format(new Date(message.sentAt), 'PPp')}
          </div>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-slate-400 hover:text-slate-300 transition-colors shrink-0"
        >
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 border-t border-slate-800/50 pt-3">
          {message.bodyText ? (
            <div className="text-sm text-slate-300 whitespace-pre-wrap max-h-64 overflow-y-auto">
              {message.bodyText}
            </div>
          ) : message.bodyHtml ? (
            <div
              className="text-sm text-slate-300 max-h-64 overflow-y-auto prose prose-invert prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: message.bodyHtml }}
            />
          ) : (
            <p className="text-sm text-slate-500 italic">No message body available</p>
          )}
        </div>
      )}
    </div>
  );
}
