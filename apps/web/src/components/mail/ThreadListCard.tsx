import { useState } from 'react';
import { cn } from '@/lib/utils';
import { ThreadList } from './ThreadList';
import { ThreadViewer } from './ThreadViewer';
import type { AgentCard } from '@/types/agent';
import { Badge } from '@/components/ui/badge';

interface ThreadListCardProps {
  card: AgentCard;
}

export function ThreadListCard({ card }: ThreadListCardProps) {
  if (card.kind !== 'thread_list' || !card.threads) {
    console.warn('ThreadListCard received non-thread_list card:', card);
    return null;
  }

  const threads = card.threads;
  const [selectedId, setSelectedId] = useState<string | null>(
    threads[0]?.threadId ?? null
  );

  const selectedSummary = threads.find((t) => t.threadId === selectedId) ?? null;

  // Extract intent - prefer top-level field, fallback to meta for backwards compatibility
  const intent = card.intent ?? (card.meta?.intent as string) ?? 'generic';

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
        <div>
          <h3 className="text-sm font-semibold text-slate-100">{card.title}</h3>
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
        />

        <div className="md:mt-0">
          <ThreadViewer threadId={selectedId} summary={selectedSummary} />
        </div>
      </div>
    </div>
  );
}
