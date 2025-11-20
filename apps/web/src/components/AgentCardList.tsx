/**
 * AgentCardList Component
 *
 * Renders Agent v2 result cards with kind-specific layouts.
 * Supports all card types: suspicious, bills, interviews, followups, generic, error.
 */

import React from 'react';
import type { AgentCard } from '@/types/agent';

export type FeedbackLabel = 'helpful' | 'not_helpful' | 'hide' | 'done';

interface AgentCardListProps {
  cards: AgentCard[];
  onFeedback?: (cardId: string, label: FeedbackLabel, itemId?: string) => void;
}

export const AgentCardList: React.FC<AgentCardListProps> = ({ cards, onFeedback }) => {
  if (!cards || cards.length === 0) return null;

  return (
    <div className="mt-4 space-y-3" data-testid="agent-card-list">
      {cards.map((card, idx) => (
        <div
          key={`${card.kind}-${idx}`}
          className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-4 shadow-sm backdrop-blur-sm"
          data-testid={`agent-card-${card.kind}`}
        >
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-zinc-100">
              {card.title}
            </h3>
            <div className="flex items-center gap-2">
              <span className="text-[11px] uppercase tracking-wide text-zinc-500">
                {card.kind.replace(/_/g, ' ')}
              </span>

              {/* Feedback controls */}
              {onFeedback && (
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    data-testid={`agent-feedback-${card.kind}-helpful`}
                    className="rounded-md border border-zinc-700/50 px-1.5 py-0.5 text-xs hover:bg-zinc-800 hover:border-zinc-600 transition-colors"
                    onClick={() => onFeedback(card.kind, 'helpful')}
                    title="Helpful"
                  >
                    👍
                  </button>
                  <button
                    type="button"
                    data-testid={`agent-feedback-${card.kind}-not-helpful`}
                    className="rounded-md border border-zinc-700/50 px-1.5 py-0.5 text-xs hover:bg-zinc-800 hover:border-zinc-600 transition-colors"
                    onClick={() => onFeedback(card.kind, 'not_helpful')}
                    title="Not helpful"
                  >
                    👎
                  </button>
                  <button
                    type="button"
                    data-testid={`agent-feedback-${card.kind}-hide`}
                    className="rounded-md border border-zinc-700/50 px-1.5 py-0.5 text-xs text-zinc-400 hover:bg-zinc-800 hover:border-zinc-600 hover:text-zinc-300 transition-colors"
                    onClick={() => onFeedback(card.kind, 'hide')}
                    title="Hide this card"
                  >
                    Hide
                  </button>
                </div>
              )}
            </div>
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
      const items = (meta.items as any[]) ?? [];
      const riskyDomains = (meta.risky_domains as string[]) ?? [];
      const timeWindowDays = meta.time_window_days as number | undefined;

      return (
        <div className="space-y-2 text-sm text-zinc-200">
          <div className="grid gap-2 md:grid-cols-2">
            <MetricPill
              label="Suspicious emails"
              value={count ?? items.length}
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

          {/* Render individual suspicious email items */}
          {items.length > 0 && (
            <div className="mt-3 space-y-2">
              {items.slice(0, 10).map((item: any, idx: number) => (
                <div
                  key={item.id || idx}
                  className="rounded-md border border-zinc-700/50 bg-zinc-800/30 px-3 py-2"
                >
                  <div className="font-medium text-zinc-100 text-sm">
                    {item.subject || 'No subject'}
                  </div>
                  <div className="mt-1 flex items-center justify-between text-xs text-zinc-400">
                    <span>{item.sender || 'Unknown sender'}</span>
                    {item.risk_level && (
                      <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-amber-200">
                        Risk: {item.risk_level}
                      </span>
                    )}
                  </div>
                  {item.reasons && Array.isArray(item.reasons) && item.reasons.length > 0 && (
                    <div className="mt-1.5 text-xs text-zinc-500">
                      {item.reasons.slice(0, 2).join(' • ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

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
      // Backend uses sections array with nested items
      const sections = (meta.sections as any[]) ?? [];

      // Extract items from sections or use legacy flat arrays
      const dueSoonSection = sections.find((s: any) => s.id === 'due_soon');
      const overdueSection = sections.find((s: any) => s.id === 'overdue');
      const otherSection = sections.find((s: any) => s.id === 'other');

      const dueSoon = dueSoonSection?.items ?? ((meta.due_soon as any[]) ?? []);
      const overdue = overdueSection?.items ?? ((meta.overdue as any[]) ?? []);
      const other = otherSection?.items ?? ((meta.other as any[]) ?? []);

      // Use counts from meta if available, otherwise calculate from arrays
      const dueSoonCount = meta.due_soon ?? dueSoon.length;
      const overdueCount = meta.overdue ?? overdue.length;
      const otherCount = meta.other ?? other.length;

      return (
        <div className="space-y-2 text-sm text-zinc-200">
          <div className="grid gap-2 md:grid-cols-3">
            <MetricPill
              label="Due soon"
              value={dueSoonCount}
              variant={dueSoonCount > 0 ? 'warning' : 'neutral'}
            />
            <MetricPill
              label="Overdue"
              value={overdueCount}
              variant={overdueCount > 0 ? 'danger' : 'neutral'}
            />
            <MetricPill
              label="Other"
              value={otherCount}
              variant="neutral"
            />
          </div>

          {/* Show due soon bills */}
          {dueSoon.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-medium text-amber-200 mb-1.5">Due soon:</p>
              <div className="space-y-1.5">
                {dueSoon.slice(0, 5).map((bill: any, idx: number) => (
                  <div
                    key={bill.id || idx}
                    className="flex justify-between items-center rounded-md border border-amber-500/20 bg-amber-500/10 px-3 py-1.5 text-xs"
                  >
                    <span className="text-zinc-200">
                      {bill.merchant || bill.sender || bill.subject || 'Bill'}
                    </span>
                    <div className="flex items-center gap-2">
                      {bill.amount && (
                        <span className="font-semibold text-zinc-100">
                          ${typeof bill.amount === 'number' ? bill.amount.toFixed(2) : bill.amount}
                        </span>
                      )}
                      {bill.due_date && (
                        <span className="text-zinc-400">
                          {new Date(bill.due_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Show overdue bills */}
          {overdue.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-medium text-red-200 mb-1.5">Overdue:</p>
              <div className="space-y-1.5">
                {overdue.slice(0, 5).map((bill: any, idx: number) => (
                  <div
                    key={bill.id || idx}
                    className="flex justify-between items-center rounded-md border border-red-500/20 bg-red-500/10 px-3 py-1.5 text-xs"
                  >
                    <span className="text-zinc-200">
                      {bill.merchant || bill.sender || bill.subject || 'Bill'}
                    </span>
                    <div className="flex items-center gap-2">
                      {bill.amount && (
                        <span className="font-semibold text-zinc-100">
                          ${typeof bill.amount === 'number' ? bill.amount.toFixed(2) : bill.amount}
                        </span>
                      )}
                      {bill.due_date && (
                        <span className="text-zinc-400">
                          {new Date(bill.due_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Show other bills if not too many */}
          {other.length > 0 && other.length <= 3 && (
            <div className="mt-3">
              <p className="text-xs font-medium text-zinc-400 mb-1.5">Other:</p>
              <div className="space-y-1.5">
                {other.map((bill: any, idx: number) => (
                  <div
                    key={bill.id || idx}
                    className="flex justify-between items-center rounded-md border border-zinc-700/50 bg-zinc-800/30 px-3 py-1.5 text-xs"
                  >
                    <span className="text-zinc-300">
                      {bill.merchant || bill.sender || bill.subject || 'Bill'}
                    </span>
                    {bill.amount && (
                      <span className="font-medium text-zinc-200">
                        ${typeof bill.amount === 'number' ? bill.amount.toFixed(2) : bill.amount}
                      </span>
                    )}
                  </div>
                ))}
              </div>
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
      const items = (meta.items as any[]) ?? [];
      const top = (meta.top as any[]) ?? [];

      // Use items if available, fallback to top for backward compatibility
      const displayItems = items.length > 0 ? items : top;

      return (
        <div className="space-y-2 text-sm text-zinc-200">
          <MetricPill
            label="Suggested follow-ups"
            value={count ?? displayItems.length}
            variant={displayItems.length > 0 ? 'success' : 'neutral'}
          />

          {/* Render individual followup items */}
          {displayItems.length > 0 && (
            <div className="mt-3 space-y-2">
              {displayItems.slice(0, 5).map((item: any, idx: number) => (
                <div
                  key={item.id || idx}
                  className="rounded-md border border-zinc-700/50 bg-zinc-800/30 px-3 py-2"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      {item.company && (
                        <div className="font-semibold text-zinc-100 text-sm">
                          {item.company}
                        </div>
                      )}
                      {item.subject && !item.company && (
                        <div className="font-medium text-zinc-100 text-sm">
                          {item.subject}
                        </div>
                      )}
                      {item.role && (
                        <div className="text-xs text-zinc-400 mt-0.5">
                          {item.role}
                        </div>
                      )}
                      {item.last_received_at && (
                        <div className="text-xs text-zinc-500 mt-1">
                          Last contact: {new Date(item.last_received_at).toLocaleDateString()}
                        </div>
                      )}
                      {item.suggested_angle && (
                        <div className="text-xs text-zinc-400 mt-1.5 italic">
                          💡 {item.suggested_angle}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
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
