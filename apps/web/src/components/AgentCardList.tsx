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
import { useMailboxThemeContext } from '@/themes/mailbox/context';

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
  const theme = useMailboxThemeContext();

  if (!cards || cards.length === 0) return null;

  return (
    <div className="flex flex-col gap-3" data-testid="agent-card-list">
      {cards.map((card, idx) => {
        const intent = getIntentFromKind(card.kind as CardKind);
        const Icon = getIconForIntent(intent);
        const meta = card.meta ?? {};
        const items = Array.isArray(meta.items) ? meta.items : [];
        const count = meta.count ?? items.length ?? null;
        const timeWindowDays = meta.time_window_days ?? meta.timeWindowDays;

        // Map intent to theme color
        const intentColor =
          intent === 'suspicious'
            ? theme.colors.intentDanger
            : intent === 'bills'
            ? theme.colors.intentInfo
            : intent === 'followups' || intent === 'interviews'
            ? theme.colors.intentSuccess
            : theme.colors.accentPrimary;

        return (
          <div
            key={`${card.kind}-${idx}`}
            className="relative flex gap-0"
            data-intent={intent}
            data-mailbox-card="true"
            data-testid={`agent-card-${card.kind}`}
          >
            {/* Left intent strip (only if theme.cards.leftIntentStrip is true) */}
            {theme.cards.leftIntentStrip && (
              <div
                aria-hidden="true"
                className="mt-2 mb-2 w-1.5 rounded-full"
                style={{
                  backgroundColor: intentColor,
                  boxShadow: `0 0 8px ${intentColor}40`,
                }}
              />
            )}

            <Card
              className={cn(
                'flex-1 overflow-hidden border-0',
                !theme.cards.leftIntentStrip && 'border',
              )}
              style={{
                backgroundColor: theme.colors.bgSurfaceElevated,
                boxShadow: theme.shadows.ambientGlow,
                borderColor: !theme.cards.leftIntentStrip ? intentColor : undefined,
              }}
            >
              <CardHeader className="flex flex-row items-start gap-3 pb-2">
                <div
                  className={cn(
                    'mt-0.5 flex h-9 w-9 items-center justify-center rounded-2xl',
                  )}
                  style={{
                    backgroundColor: theme.colors.bgSurfaceInteractive,
                    color: intentColor,
                    boxShadow: `0 0 12px ${intentColor}30`,
                  }}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <div className="flex-1 space-y-1">
                  <CardTitle
                    className="text-sm font-semibold"
                    style={{ color: theme.colors.textPrimary }}
                    data-testid="agent-card-title"
                  >
                    {card.title}
                  </CardTitle>
                  {card.body && (
                    <CardDescription
                      className="text-xs"
                      style={{ color: theme.colors.textMuted }}
                    >
                      {card.body}
                    </CardDescription>
                  )}

                  {/* metrics row */}
                  {theme.cards.headerMetricsPill && (
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px]">
                      {typeof count === 'number' && (
                        <Badge
                          variant="outline"
                          className="border-0 px-2 py-0.5 text-[11px] font-medium"
                          style={{
                            backgroundColor: `${intentColor}15`,
                            color: intentColor,
                          }}
                          data-testid="agent-card-count"
                        >
                          {count} {count === 1 ? 'item' : 'items'}
                        </Badge>
                      )}
                      {typeof timeWindowDays === 'number' && (
                        <span
                          className="rounded-full px-2 py-0.5"
                          style={{
                            backgroundColor: theme.colors.bgSurfaceInteractive,
                            color: theme.colors.textMuted,
                          }}
                        >
                          Last {timeWindowDays} days
                        </span>
                      )}
                    </div>
                  )}
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
                          'flex items-start gap-2 rounded-lg px-2 py-1.5 transition-colors',
                          theme.cards.hoverHighlightUsesIntentColor && 'hover:bg-opacity-10',
                        )}
                        style={{
                          color: theme.colors.textPrimary,
                          ...(theme.cards.hoverHighlightUsesIntentColor && {
                            '--hover-bg': `${intentColor}20`,
                          } as React.CSSProperties),
                        }}
                        data-testid="agent-card-item"
                      >
                        <ChevronRight
                          className="mt-[3px] h-3 w-3"
                          style={{ color: theme.colors.textMuted }}
                        />
                        <div className="flex-1">
                          <div className="font-medium">
                            {item.subject ?? item.title ?? 'Untitled'}
                          </div>
                          {(item.sender || item.from) && (
                            <div
                              className="text-[11px]"
                              style={{ color: theme.colors.textMuted }}
                            >
                              {item.sender ?? item.from}
                            </div>
                          )}
                        </div>
                      </li>
                    ))}
                    {items.length > 3 && (
                      <div
                        className="pt-1 text-[11px]"
                        style={{ color: theme.colors.textMuted }}
                      >
                        +{items.length - 3} more in this card
                      </div>
                    )}
                  </ul>
                </CardContent>
              )}

              {/* feedback footer */}
              {onFeedback && (
                <CardFooter
                  className="flex items-center justify-between border-t px-4 py-2.5 text-[11px]"
                  style={{
                    borderColor: theme.colors.borderSubtle,
                    backgroundColor: theme.colors.bgCanvas,
                    color: theme.colors.textMuted,
                  }}
                >
                  <span>Did this help me learn?</span>
                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 rounded-full"
                      data-testid="agent-feedback-helpful"
                      onClick={() => onFeedback(card.kind, 'helpful')}
                      style={{ color: theme.colors.intentSuccess }}
                    >
                      <ThumbsUp className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 rounded-full"
                      data-testid="agent-feedback-not-helpful"
                      onClick={() => onFeedback(card.kind, 'not_helpful')}
                      style={{ color: theme.colors.accentPrimary }}
                    >
                      <ThumbsDown className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 rounded-full"
                      data-testid="agent-feedback-hide"
                      onClick={() => onFeedback(card.kind, 'hide')}
                      style={{ color: theme.colors.textMuted }}
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
