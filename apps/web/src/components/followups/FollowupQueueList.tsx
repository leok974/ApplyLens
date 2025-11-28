import { QueueItem } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { CheckCircle2, Circle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FollowupQueueListProps {
  items: QueueItem[];
  selectedItem: QueueItem | null;
  onSelect: (item: QueueItem) => void;
  onToggleDone: (item: QueueItem, isDone: boolean) => void;
}

function getStatusColor(status?: string): string {
  switch (status) {
    case 'applied':
      return 'bg-blue-500/20 text-blue-200 border-blue-500/30';
    case 'hr_screen':
      return 'bg-purple-500/20 text-purple-200 border-purple-500/30';
    case 'interview':
      return 'bg-green-500/20 text-green-200 border-green-500/30';
    case 'offer':
      return 'bg-yellow-500/20 text-yellow-200 border-yellow-500/30';
    default:
      return 'bg-zinc-500/20 text-zinc-300 border-zinc-500/30';
  }
}

function getStatusLabel(status?: string): string {
  switch (status) {
    case 'applied':
      return 'Applied';
    case 'hr_screen':
      return 'HR Screen';
    case 'interview':
      return 'Interview';
    case 'offer':
      return 'Offer';
    default:
      return status || 'Pending';
  }
}

function getPriorityLabel(priority: 'low' | 'medium' | 'high'): string {
  return priority.charAt(0).toUpperCase() + priority.slice(1);
}

function getPriorityColor(priority: 'low' | 'medium' | 'high'): string {
  switch (priority) {
    case 'high':
      return 'border-rose-500/70 text-rose-300';
    case 'medium':
      return 'border-amber-500/70 text-amber-300';
    case 'low':
      return 'border-slate-500/60 text-slate-300';
  }
}

function getAgeString(lastMessageAt?: string): string {
  if (!lastMessageAt) return '';

  const now = new Date();
  const msgDate = new Date(lastMessageAt);
  const diffMs = now.getTime() - msgDate.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return '1d ago';
  return `${diffDays}d ago`;
}

export function FollowupQueueList({
  items,
  selectedItem,
  onSelect,
  onToggleDone,
}: FollowupQueueListProps) {
  return (
    <div className="space-y-2" data-testid="followup-queue-list">
      {items.map((item) => {
        const isSelected = selectedItem?.thread_id === item.thread_id;
        const displayTitle = item.company && item.role
          ? `${item.company} - ${item.role}`
          : item.subject || item.snippet || 'No subject';

        const ageStr = getAgeString(item.last_message_at);

        return (
          <Card
            key={item.thread_id}
            data-testid="followup-row"
            data-thread-id={item.thread_id}
            className={cn(
              'p-3 cursor-pointer transition-all border',
              isSelected
                ? 'bg-zinc-800 border-zinc-600'
                : 'bg-zinc-900/50 border-zinc-800 hover:bg-zinc-800/80',
              item.is_done && 'opacity-50 line-through'
            )}
            onClick={() => onSelect(item)}
          >
            <div className="flex items-start gap-3">
              {/* Done checkbox */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleDone(item, !item.is_done);
                }}
                className="mt-0.5 flex-shrink-0"
                data-testid="toggle-done-button"
              >
                {item.is_done ? (
                  <CheckCircle2 className="h-5 w-5 text-green-400" />
                ) : (
                  <Circle className="h-5 w-5 text-zinc-600 hover:text-zinc-400" />
                )}
              </button>

              {/* Content */}
              <div className="flex-1 min-w-0">
                {/* Title */}
                <div className="font-medium text-sm text-zinc-100 mb-1 truncate">
                  {displayTitle}
                </div>

                {/* Snippet */}
                {item.snippet && !item.is_done && (
                  <div className="text-xs text-zinc-400 mb-2 line-clamp-2">
                    {item.snippet}
                  </div>
                )}

                {/* Badges */}
                <div className="flex flex-wrap gap-1.5">
                  {/* Status badge */}
                  {item.status && (
                    <Badge
                      variant="outline"
                      className={cn('text-xs px-1.5 py-0', getStatusColor(item.status))}
                    >
                      {getStatusLabel(item.status)}
                    </Badge>
                  )}

                  {/* Priority badge */}
                  <Badge
                    variant="outline"
                    className={cn('text-xs px-1.5 py-0', getPriorityColor(item.priority))}
                  >
                    {getPriorityLabel(item.priority)}
                  </Badge>

                  {/* Age chip */}
                  {ageStr && (
                    <Badge variant="outline" className="text-xs px-1.5 py-0 bg-zinc-700/30 text-zinc-300 border-zinc-600/30">
                      {ageStr}
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
