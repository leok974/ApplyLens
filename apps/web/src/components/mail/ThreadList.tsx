import { cn } from '@/lib/utils';
import { useMailboxTheme } from '@/hooks/useMailboxTheme';
import type { MailThreadSummary } from '@/lib/mailThreads';
import { formatDistanceToNow } from 'date-fns';
import { Badge } from '@/components/ui/badge';

interface ThreadListProps {
  threads: MailThreadSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  intent: string;
}

export function ThreadList({ threads, selectedId, onSelect, intent }: ThreadListProps) {
  const { theme } = useMailboxTheme();

  if (threads.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800/50 bg-slate-950/30 p-6 text-center">
        <p className="text-sm text-slate-400">No threads found</p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5" data-testid="thread-list">
      {threads.map((thread) => {
        const isSelected = thread.threadId === selectedId;
        const isRisky = (thread.riskScore ?? 0) > 0.7;
        const hasFollowUp = intent === 'followups';

        return (
          <button
            key={thread.threadId}
            data-testid="thread-row"
            data-thread-id={thread.threadId}
            data-selected={isSelected ? 'true' : 'false'}
            onClick={() => onSelect(thread.threadId)}
            className={cn(
              'w-full rounded-lg border p-3 text-left transition-all',
              'hover:border-slate-700/70 focus:outline-none focus:ring-2 focus:ring-yellow-400/30',
              isSelected
                ? [
                    'border-yellow-400/30 bg-slate-900/60',
                    theme.id === 'bananaPro' && 'shadow-[0_0_20px_rgba(250,204,21,0.2)]',
                  ]
                : 'border-slate-800/50 bg-slate-950/30'
            )}
            aria-selected={isSelected}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h4
                    className={cn(
                      'text-sm font-medium truncate',
                      isSelected ? 'text-slate-100' : 'text-slate-200'
                    )}
                  >
                    {thread.subject}
                  </h4>
                  {isRisky && (
                    <Badge variant="destructive" className="text-xs px-1.5 py-0">
                      Risk
                    </Badge>
                  )}
                  {hasFollowUp && (
                    <Badge variant="outline" className="text-xs px-1.5 py-0 border-yellow-400/30 text-yellow-400">
                      Follow-up
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-slate-400 truncate mb-1">{thread.from}</p>
                <p className="text-xs text-slate-500 line-clamp-2">{thread.snippet}</p>
              </div>

              <div className="flex flex-col items-end gap-1 text-xs text-slate-500 shrink-0">
                <span>{formatDistanceToNow(new Date(thread.lastMessageAt), { addSuffix: true })}</span>
                {thread.labels.length > 0 && (
                  <div className="flex gap-1 flex-wrap justify-end">
                    {thread.labels.slice(0, 2).map((label) => (
                      <span
                        key={label}
                        className="inline-block rounded bg-slate-800/50 px-1.5 py-0.5 text-[10px]"
                      >
                        {label}
                      </span>
                    ))}
                    {thread.labels.length > 2 && (
                      <span className="inline-block px-1.5 py-0.5 text-[10px]">
                        +{thread.labels.length - 2}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
