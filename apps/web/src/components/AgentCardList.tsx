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
import { useMailboxTheme } from '@/hooks/useMailboxTheme';
import { getMailboxThemeClasses } from '@/themes/mailbox/classes';

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
import { ThreadListCard } from '@/components/mail/ThreadListCard';

type CardKind =
  | 'suspicious_summary'
  | 'bills_summary'
  | 'followups_summary'
  | 'interviews_summary'
  | 'profile_summary'
  | 'generic_summary'
  | string;

type IntentType = 'suspicious' | 'bills' | 'followups' | 'interviews' | 'profile' | 'generic';

// Map card kind to intent type
function getIntentFromKind(kind: string): IntentType {
  if (kind === 'suspicious_summary') return 'suspicious';
  if (kind === 'bills_summary') return 'bills';
  if (kind === 'followups_summary') return 'followups';
  if (kind === 'interviews_summary') return 'interviews';
  if (kind === 'profile_summary') return 'profile';
  return 'generic';
}

// Map intent to icon
function getIconForIntent(intent: IntentType): React.ComponentType<React.SVGProps<SVGSVGElement>> {
  switch (intent) {
    case 'suspicious': return ShieldAlert;
    case 'bills': return ReceiptText;
    case 'followups': return BellRing;
    case 'interviews': return UserSearch;
    case 'profile': return MailSearch;
    default: return Sparkles;
  }
}

export type FeedbackLabel = 'helpful' | 'not_helpful' | 'hide' | 'done';

interface AgentCardListProps {
  cards: AgentCard[];
  onFeedback?: (cardId: string, label: FeedbackLabel, itemId?: string) => void;
}

export const AgentCardList: React.FC<AgentCardListProps> = ({ cards, onFeedback }) => {
  const { themeId, theme } = useMailboxTheme();
  const themeClasses = getMailboxThemeClasses(themeId);

  if (!cards || cards.length === 0) return null;

  return (
    <div className="flex flex-col gap-3" data-testid="agent-card-list">
      {cards.map((card, idx) => {
        // Handle thread_list cards separately
        if (card.kind === 'thread_list') {
          return <ThreadListCard key={`thread-list-${idx}`} card={card} />;
        }

        const intent = getIntentFromKind(card.kind as CardKind);
        const Icon = getIconForIntent(intent);
        const meta = card.meta ?? {};
        const items = Array.isArray(meta.items) ? meta.items : [];
        const count = meta.count ?? items.length ?? null;
        const timeWindowDays = meta.time_window_days ?? meta.timeWindowDays;

        // Map intent to theme class
        const intentStripClass =
          intent === 'suspicious'
            ? themeClasses.intentStripSuspicious
            : intent === 'bills'
            ? themeClasses.intentStripBills
            : themeClasses.intentStripFollowups;

        // Get hover background for Banana Pro
        const hoverBg =
          themeId === 'bananaPro' && theme.card?.intent
            ? intent === 'suspicious'
              ? theme.card.intent.suspicious.hoverBg
              : intent === 'bills'
              ? theme.card.intent.bills.hoverBg
              : theme.card.intent.followups.hoverBg
            : undefined;

        return (
          <div
            key={`${card.kind}-${idx}`}
            className="relative flex gap-0"
            data-intent={intent}
            data-mailbox-card="true"
            data-testid={`agent-card-${card.kind}`}
          >
            {/* Left intent strip with glow */}
            <div
              aria-hidden="true"
              className={cn('mt-2 mb-2 ml-0.5 w-1.5 rounded-full', intentStripClass)}
            />

            <Card
              className={cn(
                'flex-1 overflow-hidden ml-3',
                themeClasses.agentCardBase,
              )}
            >
              <CardHeader className={cn("flex flex-row items-start gap-3 pb-2", themeClasses.agentCardHeader)}>
                <div
                  className={cn(
                    'mt-0.5 flex h-9 w-9 items-center justify-center rounded-2xl bg-slate-800/50',
                  )}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <div className="flex-1 space-y-1">
                  <CardTitle
                    className={cn("text-sm font-semibold", themeClasses.agentCardHeader)}
                    data-testid="agent-card-title"
                  >
                    {card.title}
                  </CardTitle>
                  {card.body && (
                    <CardDescription
                      className="text-xs text-slate-400"
                    >
                      {card.body}
                    </CardDescription>
                  )}

                  {/* metrics row */}
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px]">
                    {typeof count === 'number' && (
                      <Badge
                        variant="outline"
                        className="border-slate-700 px-2 py-0.5 text-[11px] font-medium text-slate-300"
                        data-testid="agent-card-count"
                      >
                        {count} {count === 1 ? 'item' : 'items'}
                      </Badge>
                    )}
                    {typeof timeWindowDays === 'number' && (
                      <span
                        className="rounded-full bg-slate-800/50 px-2 py-0.5 text-slate-400"
                      >
                        Last {timeWindowDays} days
                      </span>
                    )}
                  </div>
                </div>
              </CardHeader>

              {/* list preview if we have items */}
              {items.length > 0 && (
                <CardContent className="pt-1">
                  <ul className="space-y-1.5 text-xs">
                    {items.slice(0, 3).map((item: any, idx: number) => (
                      <li
                        key={item.id ?? item.thread_id ?? idx}
                        className={cn(
                          "flex items-start gap-2 rounded-lg px-2 py-1.5 text-slate-50 transition-colors",
                          themeId === 'bananaPro'
                            ? `hover:bg-[${hoverBg}]`
                            : "hover:bg-slate-800/30"
                        )}
                        style={
                          themeId === 'bananaPro' && hoverBg
                            ? { '--hover-bg': hoverBg } as React.CSSProperties
                            : undefined
                        }
                        data-testid="agent-card-item"
                      >
                        <ChevronRight
                          className="mt-[3px] h-3 w-3 text-slate-400"
                        />
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

              {/* feedback footer */}
              {onFeedback && (
                <CardFooter
                  className={cn(
                    "flex items-center justify-between px-4 py-2.5 text-[11px]",
                    themeClasses.agentCardFooter
                  )}
                >
                  <span>Did this help me learn?</span>
                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="ghost"
                      size="icon"
                      className={cn(
                        "h-7 w-7 rounded-full",
                        themeId === 'bananaPro'
                          ? "text-yellow-300/80 hover:bg-yellow-400/10 hover:text-yellow-200 border border-transparent hover:border-yellow-300/50"
                          : "text-emerald-400 hover:text-emerald-300"
                      )}
                      data-testid="agent-feedback-helpful"
                      onClick={() => onFeedback(card.kind, 'helpful')}
                    >
                      <ThumbsUp className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className={cn(
                        "h-7 w-7 rounded-full",
                        themeId === 'bananaPro'
                          ? "text-yellow-300/80 hover:bg-yellow-400/10 hover:text-yellow-200 border border-transparent hover:border-yellow-300/50"
                          : "text-sky-400 hover:text-sky-300"
                      )}
                      data-testid="agent-feedback-not-helpful"
                      onClick={() => onFeedback(card.kind, 'not_helpful')}
                    >
                      <ThumbsDown className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className={cn(
                        "h-7 w-7 rounded-full",
                        themeId === 'bananaPro'
                          ? "text-yellow-300/80 hover:bg-yellow-400/10 hover:text-yellow-200 border border-transparent hover:border-yellow-300/50"
                          : "text-slate-400 hover:text-slate-300"
                      )}
                      data-testid="agent-feedback-hide"
                      onClick={() => onFeedback(card.kind, 'hide')}
                    >
                      <EyeOff className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </CardFooter>
              )}
            </Card>
          </div>
        );
      })}
    </div>
  );
};
