/**
 * AgentCard - Renders structured agent response cards
 *
 * Displays different card types from Agent v2 responses:
 * - suspicious_summary: Risky emails with security analysis
 * - bills_summary: Upcoming bills and payment deadlines
 * - followups_summary: Emails needing follow-up
 * - interviews_summary: Scheduled interviews
 * - generic_summary: General email summaries
 * - error: Error states
 */

import type { AgentCard } from '../types/agent';

interface AgentCardProps {
  card: AgentCard;
  index?: number;
}

function kindLabel(kind: AgentCard['kind']): string {
  switch (kind) {
    case 'suspicious_summary':
      return 'Suspicious emails';
    case 'bills_summary':
      return 'Bills & invoices';
    case 'followups_summary':
      return 'Follow-ups';
    case 'interviews_summary':
      return 'Interviews';
    case 'generic_summary':
      return 'Summary';
    case 'error':
      return 'Agent error';
    default:
      return kind;
  }
}

function getScanSubtitle(card: AgentCard): string | undefined {
  const intent = card.intent ?? (card.kind?.replace('_summary', '') ?? '');

  switch (intent) {
    case 'followups':
      return 'Conversations waiting on your reply';
    case 'unsubscribe':
      return 'Newsletters you haven\'t opened recently';
    case 'clean_promos':
      return 'Promotions you may want to archive';
    case 'bills':
      return 'Bills and payment reminders from your inbox';
    case 'interviews':
      return 'Interview and recruiter threads';
    case 'suspicious':
      return 'Emails that might be risky';
    default:
      return undefined;
  }
}

export function AgentResultCard({ card }: AgentCardProps) {
  const count =
    typeof card.meta?.count === 'number'
      ? (card.meta.count as number)
      : undefined;

  const timeWindow =
    typeof card.meta?.time_window_days === 'number'
      ? (card.meta.time_window_days as number)
      : undefined;

  const subtitle = getScanSubtitle(card);

  return (
    <div
      className="mt-2 rounded-lg border border-neutral-700/40 bg-neutral-800/40 p-3 text-sm"
      data-testid="agent-card"
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="inline-flex items-center rounded-full border border-neutral-600/60 px-2 py-0.5 text-[11px] uppercase tracking-wide text-neutral-300">
          {kindLabel(card.kind)}
        </span>
        {count != null && timeWindow != null && (
          <div
            data-testid="agent-card-meta-pill"
            className="ml-auto text-xs text-slate-300/80"
          >
            {count} {count === 1 ? 'item' : 'items'} · last {timeWindow} days
          </div>
        )}
      </div>

      <div className="font-medium mb-1 text-neutral-100">{card.title}</div>
      {subtitle && (
        <p className="mt-1 text-xs text-slate-300/80" data-testid="agent-card-subtitle">
          {subtitle}
        </p>
      )}
      <p className="text-sm text-neutral-300 whitespace-pre-line">
        {card.body}
      </p>
    </div>
  );
}
