import { cn } from '@/lib/utils';
import { useMailboxTheme } from '@/hooks/useMailboxTheme';
import type { MailThreadSummary } from '@/lib/mailThreads';
import { formatDistanceToNow } from 'date-fns';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Plus, ExternalLink } from 'lucide-react';

interface ThreadListProps {
  threads: MailThreadSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  intent: string;
  onCreateApplication?: (threadId: string) => void;
  onOpenTracker?: (applicationId: number) => void;
}

export function ThreadList({
  threads,
  selectedId,
  onSelect,
  intent,
  onCreateApplication,
  onOpenTracker
}: ThreadListProps) {
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
                  {thread.applicationStatus && (
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-xs px-1.5 py-0',
                        thread.applicationStatus === 'offer' && 'border-emerald-400/30 text-emerald-400',
                        thread.applicationStatus === 'interview' && 'border-blue-400/30 text-blue-400',
                        thread.applicationStatus === 'rejected' && 'border-red-400/30 text-red-400',
                        thread.applicationStatus === 'applied' && 'border-slate-400/30 text-slate-400',
                        thread.applicationStatus === 'hr_screen' && 'border-cyan-400/30 text-cyan-400',
                        thread.applicationStatus === 'on_hold' && 'border-orange-400/30 text-orange-400',
                        thread.applicationStatus === 'ghosted' && 'border-slate-500/30 text-slate-500'
                      )}
                      data-testid="thread-app-status-badge"
                    >
                      {thread.applicationStatus === 'hr_screen' ? 'HR Screen' :
                       thread.applicationStatus === 'on_hold' ? 'On Hold' :
                       thread.applicationStatus.charAt(0).toUpperCase() + thread.applicationStatus.slice(1)}
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-slate-400 truncate mb-1">{thread.from}</p>
                <p className="text-xs text-slate-500 line-clamp-2">{thread.snippet}</p>
              </div>

              <div className="flex flex-col items-end gap-1.5 text-xs text-slate-500 shrink-0">
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
                {/* Application action buttons */}
                {(intent === 'followups' || intent === 'interviews') && (
                  <div className="mt-1" onClick={(e) => e.stopPropagation()}>
                    {thread.applicationId ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 px-2 text-[10px] text-yellow-400/90 hover:text-yellow-400 hover:bg-yellow-400/10"
                        onClick={() => onOpenTracker?.(thread.applicationId!)}
                        data-testid="thread-action-open-tracker"
                        data-application-id={thread.applicationId}
                      >
                        <ExternalLink className="h-3 w-3 mr-1" />
                        Open in Tracker
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 px-2 text-[10px] text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                        onClick={() => onCreateApplication?.(thread.threadId)}
                        data-testid="thread-action-create"
                      >
                        <Plus className="h-3 w-3 mr-1" />
                        Create application
                      </Button>
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
