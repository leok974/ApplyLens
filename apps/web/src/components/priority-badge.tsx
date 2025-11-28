import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { FollowupPriority } from '@/lib/api';

interface PriorityBadgeProps {
  priority: FollowupPriority;
  className?: string;
}

export function PriorityBadge({ priority, className }: PriorityBadgeProps) {
  const label = priority.charAt(0).toUpperCase() + priority.slice(1);

  return (
    <Badge
      variant="outline"
      className={cn(
        'text-xs px-1.5 py-0',
        priority === 'high' && 'border-rose-500/70 text-rose-300',
        priority === 'medium' && 'border-amber-500/70 text-amber-300',
        priority === 'low' && 'border-slate-500/60 text-slate-300',
        className
      )}
    >
      {label}
    </Badge>
  );
}
