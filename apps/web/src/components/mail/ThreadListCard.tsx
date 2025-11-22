import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { ThreadList } from './ThreadList';
import { ThreadViewer } from './ThreadViewer';
import type { AgentCard } from '@/types/agent';
import type { MailThreadSummary } from '@/lib/mailThreads';
import { Badge } from '@/components/ui/badge';
import { createApplicationFromEmail } from '@/lib/api';
import { toast } from 'sonner';

interface ThreadListCardProps {
  card: AgentCard;
}

export function ThreadListCard({ card }: ThreadListCardProps) {
  if (card.kind !== 'thread_list' || !card.threads) {
    console.warn('ThreadListCard received non-thread_list card:', card);
    return null;
  }

  const navigate = useNavigate();
  const [threads, setThreads] = useState<MailThreadSummary[]>(card.threads);
  const [selectedId, setSelectedId] = useState<string | null>(
    threads[0]?.threadId ?? null
  );
  const [creatingApp, setCreatingApp] = useState<string | null>(null);

  const selectedSummary = threads.find((t) => t.threadId === selectedId) ?? null;

  // Extract intent - prefer top-level field, fallback to meta for backwards compatibility
  const intent = card.intent ?? (card.meta?.intent as string) ?? 'generic';
  const count = card.meta?.count;
  const timeWindowDays = card.meta?.time_window_days;

  // Handler: Create application from thread
  const handleCreateApplication = async (threadId: string) => {
    const thread = threads.find((t) => t.threadId === threadId);
    if (!thread) return;

    // For now, we need to find/create an email ID from the thread
    // The API expects an email_id (int), but we have threadId (string)
    // We'll need to call a backend endpoint to get the email_id for a thread
    // For POC, we'll show a toast and update local state
    setCreatingApp(threadId);

    try {
      // TODO: Need to resolve threadId -> email_id mapping
      // For now, parse threadId as integer if possible, or call a helper endpoint
      const emailIdMatch = threadId.match(/\d+/);
      if (!emailIdMatch) {
        throw new Error('Could not extract email ID from thread');
      }
      const emailId = parseInt(emailIdMatch[0], 10);

      const result = await createApplicationFromEmail(emailId);

      // Update local thread state with the new application ID
      setThreads((prev) =>
        prev.map((t) =>
          t.threadId === threadId
            ? { ...t, applicationId: result.application_id, applicationStatus: 'active' }
            : t
        )
      );

      toast.success('Application created from this thread');
    } catch (error) {
      console.error('Failed to create application:', error);
      toast.error('Failed to create application');
    } finally {
      setCreatingApp(null);
    }
  };

  // Handler: Open tracker with application pre-selected
  const handleOpenTracker = (applicationId: number) => {
    navigate(`/applications?highlight=${applicationId}`);
  };

  return (
    <div
      className={cn(
        'mt-4 rounded-3xl border p-4 md:p-5',
        'border-slate-800/70 bg-slate-950/80'
      )}
      data-testid="thread-card"
    >
      {/* Header */}
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-100">{card.title}</h3>
            {count != null && timeWindowDays != null && (
              <div
                data-testid="agent-card-meta-pill"
                className="text-xs text-slate-300/80"
              >
                {count} {count === 1 ? 'item' : 'items'} · last {timeWindowDays} days
              </div>
            )}
          </div>
          {card.body && (
            <p className="mt-1 text-xs text-slate-400">{card.body}</p>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Intent badge */}
          {intent && intent !== 'generic' && (
            <Badge
              variant="outline"
              className={cn(
                'text-xs',
                intent === 'suspicious' && 'border-red-400/30 text-red-400',
                intent === 'followups' && 'border-yellow-400/30 text-yellow-400',
                intent === 'bills' && 'border-blue-400/30 text-blue-400',
                intent === 'interviews' && 'border-purple-400/30 text-purple-400',
                intent === 'unsubscribe' && 'border-orange-400/30 text-orange-400',
                intent === 'clean_promos' && 'border-green-400/30 text-green-400'
              )}
            >
              {intent}
            </Badge>
          )}

          {/* Thread count */}
          <Badge variant="secondary" className="text-xs">
            {threads.length} {threads.length === 1 ? 'thread' : 'threads'}
          </Badge>
        </div>
      </div>

      {/* 2-column layout: list + viewer */}
      <div className="mt-3 flex flex-col gap-4 md:grid md:grid-cols-[minmax(0,1.1fr)_minmax(0,1.3fr)] md:gap-4">
        <ThreadList
          threads={threads}
          selectedId={selectedId}
          onSelect={setSelectedId}
          intent={intent}
          onCreateApplication={handleCreateApplication}
          onOpenTracker={handleOpenTracker}
        />

        <div className="md:mt-0">
          <ThreadViewer
            threadId={selectedId}
            summary={selectedSummary}
            onCreateApplication={handleCreateApplication}
          />
        </div>
      </div>

      {/* UX hint for scan intents */}
      {card.kind === 'thread_list' && card.intent && (
        <p className="mt-2 text-xs text-slate-400/80">
          Click a conversation to see details here, or open it in Gmail to reply.
        </p>
      )}
    </div>
  );
}
