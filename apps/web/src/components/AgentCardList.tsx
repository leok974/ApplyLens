/**
 * AgentCardList Component
 *
 * Renders Agent v2 result cards with kind-specific layouts.
 * Supports all card types: suspicious, bills, interviews, followups, generic, error.
 */

import React from 'react';
import type { AgentCard } from '@/types/agent';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

import {
  ShieldAlert,
  ReceiptText,
  BellRing,
  UserSearch,
  Sparkles,
  MailSearch,
  ChevronRight,
  ThumbsUp,
  ThumbsDown,
  EyeOff,
} from 'lucide-react';

type CardKind =
  | 'suspicious_summary'
  | 'bills_summary'
  | 'followups_summary'
  | 'interviews_summary'
  | 'profile_summary'
  | 'generic_summary'
  | string;

const CARD_STYLE: Record<
  string,
  {
    Icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
    accentBorder: string;
    accentBg: string;
    iconBg: string;
    iconColor: string;
    pillBg: string;
  }
> = {
  suspicious_summary: {
    Icon: ShieldAlert,
    accentBorder: 'border-red-500/60',
    accentBg: 'bg-red-500/5',
    iconBg: 'bg-red-500/15',
    iconColor: 'text-red-300',
    pillBg: 'bg-red-500/15 text-red-200',
  },
  bills_summary: {
    Icon: ReceiptText,
    accentBorder: 'border-sky-500/60',
    accentBg: 'bg-sky-500/5',
    iconBg: 'bg-sky-500/15',
    iconColor: 'text-sky-300',
    pillBg: 'bg-sky-500/15 text-sky-200',
  },
  followups_summary: {
    Icon: BellRing,
    accentBorder: 'border-indigo-500/60',
    accentBg: 'bg-indigo-500/5',
    iconBg: 'bg-indigo-500/15',
    iconColor: 'text-indigo-300',
    pillBg: 'bg-indigo-500/15 text-indigo-200',
  },
  interviews_summary: {
    Icon: UserSearch,
    accentBorder: 'border-emerald-500/60',
    accentBg: 'bg-emerald-500/5',
    iconBg: 'bg-emerald-500/15',
    iconColor: 'text-emerald-300',
    pillBg: 'bg-emerald-500/15 text-emerald-200',
  },
  profile_summary: {
    Icon: MailSearch,
    accentBorder: 'border-amber-500/60',
    accentBg: 'bg-amber-500/5',
    iconBg: 'bg-amber-500/15',
    iconColor: 'text-amber-300',
    pillBg: 'bg-amber-500/15 text-amber-200',
  },
  generic_summary: {
    Icon: Sparkles,
    accentBorder: 'border-slate-600/80',
    accentBg: 'bg-slate-500/5',
    iconBg: 'bg-slate-500/15',
    iconColor: 'text-slate-200',
    pillBg: 'bg-slate-500/15 text-slate-200',
  },
};

const getCardStyle = (kind: CardKind) =>
  CARD_STYLE[kind] ?? CARD_STYLE.generic_summary;

export type FeedbackLabel = 'helpful' | 'not_helpful' | 'hide' | 'done';

interface AgentCardListProps {
  cards: AgentCard[];
  onFeedback?: (cardId: string, label: FeedbackLabel, itemId?: string) => void;
}

export const AgentCardList: React.FC<AgentCardListProps> = ({ cards, onFeedback }) => {
  if (!cards || cards.length === 0) return null;

  return (
    <div className="flex flex-col gap-3" data-testid="agent-card-list">
      {cards.map((card, idx) => {
        const style = getCardStyle(card.kind as CardKind);
        const Icon = style.Icon;
        const meta = card.meta ?? {};
        const items = Array.isArray(meta.items) ? meta.items : [];
        const count = meta.count ?? items.length ?? null;
        const timeWindowDays = meta.time_window_days ?? meta.timeWindowDays;

        return (
          <Card
            key={`${card.kind}-${idx}`}
            className={cn(
              'border bg-slate-950/80 backdrop-blur-sm transition-colors',
              'hover:border-slate-500/70',
              style.accentBorder,
            )}
            data-testid={`agent-card-${card.kind}`}
          >
            <CardHeader className="flex flex-row items-start gap-3 pb-2">
              <div
                className={cn(
                  'mt-0.5 flex h-9 w-9 items-center justify-center rounded-2xl',
                  style.iconBg,
                )}
              >
                <Icon className={cn('h-4 w-4', style.iconColor)} />
              </div>
              <div className="flex-1 space-y-1">
                <CardTitle
                  className="text-sm font-semibold text-slate-50"
                  data-testid="agent-card-title"
                >
                  {card.title}
                </CardTitle>
                {card.body && (
                  <CardDescription className="text-xs text-slate-300/90">
                    {card.body}
                  </CardDescription>
                )}

                {/* metrics row */}
                <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                  {typeof count === 'number' && (
                    <Badge
                      variant="outline"
                      className={cn(
                        'border-0 px-2 py-0.5 text-[11px] font-medium',
                        style.pillBg,
                      )}
                      data-testid="agent-card-count"
                    >
                      {count} {count === 1 ? 'item' : 'items'}
                    </Badge>
                  )}
                  {typeof timeWindowDays === 'number' && (
                    <span className="rounded-full bg-slate-900/80 px-2 py-0.5">
                      Last {timeWindowDays} days
                    </span>
                  )}
                </div>
              </div>
            </CardHeader>

            {/* list preview if we have items */}
            {items.length > 0 && (
              <CardContent className="pt-1">
                <ul className="space-y-1.5 text-xs text-slate-100">
                  {items.slice(0, 3).map((item: any, idx: number) => (
                    <li
                      key={item.id ?? item.thread_id ?? idx}
                      className="flex items-start gap-2"
                      data-testid="agent-card-item"
                    >
                      <ChevronRight className="mt-[3px] h-3 w-3 text-slate-500" />
                      <div className="flex-1">
                        <div className="font-medium">
                          {item.subject ?? item.title ?? 'Untitled'}
                        </div>
                        {(item.sender || item.from) && (
                          <div className="text-[11px] text-slate-400">
                            {item.sender ?? item.from}
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
                  {items.length > 3 && (
                    <div className="pt-1 text-[11px] text-slate-400">
                      +{items.length - 3} more in this card
                    </div>
                  )}
                </ul>
              </CardContent>
            )}

            {/* feedback footer (wires into your existing onFeedback) */}
            {onFeedback && (
              <CardFooter className="flex items-center justify-between border-t border-slate-800/80 bg-slate-950/90 px-4 py-2.5 text-[11px] text-slate-400">
                <span>Is this helpful?</span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 rounded-full"
                    data-testid="agent-feedback-helpful"
                    onClick={() => onFeedback(card.kind, 'helpful')}
                  >
                    <ThumbsUp className="h-3.5 w-3.5 text-emerald-300" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 rounded-full"
                    data-testid="agent-feedback-not-helpful"
                    onClick={() => onFeedback(card.kind, 'not_helpful')}
                  >
                    <ThumbsDown className="h-3.5 w-3.5 text-amber-300" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 rounded-full"
                    data-testid="agent-feedback-hide"
                    onClick={() => onFeedback(card.kind, 'hide')}
                  >
                    <EyeOff className="h-3.5 w-3.5 text-slate-300" />
                  </Button>
                </div>
              </CardFooter>
            )}
          </Card>
        );
      })}
    </div>
  );
};
