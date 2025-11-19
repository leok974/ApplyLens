/**
 * AgentCardList Component
 *
 * Renders Agent v2 result cards with kind-specific layouts.
 * Supports all card types: suspicious, bills, interviews, followups, generic, error.
 */

import React from 'react';
import type { AgentCard } from '@/types/agent';

interface AgentCardListProps {
  cards: AgentCard[];
}

export const AgentCardList: React.FC<AgentCardListProps> = ({ cards }) => {
  if (!cards || cards.length === 0) return null;

  return (
    <div className="mt-4 space-y-3" data-testid="agent-card-list">
      {cards.map((card, idx) => (
        <div
          key={`${card.kind}-${idx}`}
          className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4 shadow-sm backdrop-blur-sm"
          data-testid={`agent-card-${card.kind}`}
        >
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-100">
              {card.title}
            </h3>
            <span className="text-[11px] uppercase tracking-wide text-zinc-500">
              {card.kind.replace(/_/g, ' ')}
            </span>
          </div>

          {/* Card body from card.body field */}
          {card.body && (
            <div className="mb-3 text-sm text-zinc-300 leading-relaxed">
              {card.body}
            </div>
          )}

          {/* Render kind-specific metadata */}
          {renderCardMeta(card)}

          {/* Email IDs (sources) - if present */}
          {card.email_ids && card.email_ids.length > 0 && (
            <div className="mt-3 pt-3 border-t border-zinc-800">
              <p className="text-xs text-zinc-500">
                Based on {card.email_ids.length} email{card.email_ids.length !== 1 ? 's' : ''}
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

/**
 * Render card-specific metadata based on card.kind
 */
function renderCardMeta(card: AgentCard) {
  const meta = card.meta ?? {};

  switch (card.kind) {
    case 'suspicious_summary': {
      const count = meta.count as number | undefined;
      const riskyDomains = (meta.risky_domains as string[]) ?? [];
      const timeWindowDays = meta.time_window_days as number | undefined;

      return (
        <div className="space-y-2 text-sm text-zinc-200">
          <div className="grid gap-2 md:grid-cols-2">
            <MetricPill
              label="Suspicious emails"
              value={count ?? 0}
              variant={count && count > 0 ? 'warning' : 'neutral'}
            />
            {timeWindowDays && (
              <MetricPill
                label="Time window"
                value={`${timeWindowDays}d`}
                variant="neutral"
              />
            )}
          </div>

          {riskyDomains.length > 0 && (
            <div className="mt-2">
              <p className="text-xs text-zinc-400 mb-1">Risky domains:</p>
              <ul className="list-disc pl-4 text-xs text-zinc-300 space-y-0.5">
                {riskyDomains.slice(0, 5).map((d) => (
                  <li key={d}>{d}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );
    }

    case 'bills_summary': {
      const dueSoon = (meta.due_soon as any[]) ?? [];
      const overdue = (meta.overdue as any[]) ?? [];
      const other = (meta.other as any[]) ?? [];

      return (
        <div className="space-y-2 text-sm text-zinc-200">
          <div className="grid gap-2 md:grid-cols-3">
            <MetricPill
              label="Due soon"
              value={dueSoon.length}
              variant={dueSoon.length > 0 ? 'warning' : 'neutral'}
            />
            <MetricPill
              label="Overdue"
              value={overdue.length}
              variant={overdue.length > 0 ? 'danger' : 'neutral'}
            />
            <MetricPill
              label="Other"
              value={other.length}
              variant="neutral"
            />
          </div>

          {/* Show top bills if available */}
          {dueSoon.length > 0 && (
            <div className="mt-2">
              <p className="text-xs text-zinc-400 mb-1">Due soon:</p>
              <ul className="text-xs text-zinc-300 space-y-1">
                {dueSoon.slice(0, 3).map((bill: any, idx: number) => (
                  <li key={idx} className="flex justify-between">
                    <span>{bill.sender || bill.subject}</span>
                    {bill.amount && <span className="font-semibold">{bill.amount}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );
    }

    case 'interviews_summary': {
      const upcoming = (meta.upcoming as any[]) ?? [];
      const waiting = (meta.waiting as any[]) ?? [];
      const closed = (meta.closed as any[]) ?? [];

      return (
        <div className="space-y-2 text-sm text-zinc-200">
          <div className="grid gap-2 md:grid-cols-3">
            <MetricPill
              label="Upcoming"
              value={upcoming.length}
              variant={upcoming.length > 0 ? 'success' : 'neutral'}
            />
            <MetricPill
              label="Waiting"
              value={waiting.length}
              variant={waiting.length > 0 ? 'warning' : 'neutral'}
            />
            <MetricPill
              label="Closed"
              value={closed.length}
              variant="neutral"
            />
          </div>

          {/* Show upcoming interviews */}
          {upcoming.length > 0 && (
            <div className="mt-2">
              <p className="text-xs text-zinc-400 mb-1">Upcoming interviews:</p>
              <ul className="text-xs text-zinc-300 space-y-1">
                {upcoming.slice(0, 3).map((item: any, idx: number) => (
                  <li key={idx}>
                    {item.company && <span className="font-semibold">{item.company}</span>}
                    {item.role && <span> — {item.role}</span>}
                    {item.date && <span className="text-zinc-400"> ({item.date})</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );
    }

    case 'followups_summary': {
      const count = meta.count as number | undefined;
      const top = (meta.top as any[]) ?? [];

      return (
        <div className="space-y-2 text-sm text-zinc-200">
          <MetricPill
            label="Suggested follow-ups"
            value={count ?? top.length}
            variant={top.length > 0 ? 'success' : 'neutral'}
          />

          {top.length > 0 && (
            <div className="mt-2">
              <ol className="list-decimal pl-4 text-xs text-zinc-300 space-y-1">
                {top.slice(0, 5).map((item: any, idx: number) => (
                  <li key={idx}>
                    {item.company && (
                      <span className="font-semibold">{item.company}</span>
                    )}
                    {item.role && <span> — {item.role}</span>}
                    {item.last_contact && (
                      <span className="text-zinc-400">
                        {' '}({item.last_contact})
                      </span>
                    )}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      );
    }

    case 'generic_summary': {
      // Generic fallback: show key metrics if available
      const totalEmails = meta.total_emails as number | undefined;
      const timeWindowDays = meta.time_window_days as number | undefined;
      const emailsScanned = meta.emails_scanned as number | undefined;

      const hasMetrics = totalEmails || timeWindowDays || emailsScanned;

      if (!hasMetrics) {
        return null;
      }

      return (
        <div className="grid gap-2 md:grid-cols-3 text-sm">
          {emailsScanned !== undefined && (
            <MetricPill label="Emails scanned" value={emailsScanned} variant="neutral" />
          )}
          {totalEmails !== undefined && (
            <MetricPill label="Total found" value={totalEmails} variant="neutral" />
          )}
          {timeWindowDays !== undefined && (
            <MetricPill label="Time window" value={`${timeWindowDays}d`} variant="neutral" />
          )}
        </div>
      );
    }

    case 'error': {
      const errorDetails = meta.error_details as string | undefined;
      const errorType = meta.error_type as string | undefined;

      return (
        <div className="space-y-2 text-sm">
          {errorType && (
            <p className="text-xs text-red-400 font-mono">
              {errorType}
            </p>
          )}
          {errorDetails && (
            <p className="text-xs text-zinc-400">
              {errorDetails}
            </p>
          )}
        </div>
      );
    }

    default: {
      // Unknown card kind - dump meta as key/value pairs
      const entries = Object.entries(meta ?? {});
      if (!entries.length) {
        return null;
      }

      return (
        <dl className="space-y-1 text-xs text-zinc-300">
          {entries.slice(0, 10).map(([key, value]) => (
            <div key={key} className="flex justify-between gap-4">
              <dt className="text-zinc-500 capitalize">{key.replace(/_/g, ' ')}</dt>
              <dd className="text-right font-mono">
                {typeof value === 'string' || typeof value === 'number'
                  ? value
                  : JSON.stringify(value)}
              </dd>
            </div>
          ))}
        </dl>
      );
    }
  }
}

/**
 * Metric pill component with variant styling
 */
interface MetricPillProps {
  label: string;
  value: number | string;
  variant?: 'neutral' | 'success' | 'warning' | 'danger';
}

function MetricPill({ label, value, variant = 'neutral' }: MetricPillProps) {
  const variantStyles = {
    neutral: 'border-zinc-700 bg-zinc-900/60 text-zinc-100',
    success: 'border-green-800 bg-green-950/60 text-green-200',
    warning: 'border-yellow-800 bg-yellow-950/60 text-yellow-200',
    danger: 'border-red-800 bg-red-950/60 text-red-200',
  };

  return (
    <div
      className={`rounded-full border px-3 py-1 flex items-center justify-between text-xs ${variantStyles[variant]}`}
      data-testid={`metric-${label.toLowerCase().replace(/\s+/g, '-')}`}
    >
      <span className="text-zinc-400">{label}</span>
      <span className="font-semibold ml-2">{value}</span>
    </div>
  );
}
