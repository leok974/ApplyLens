# Thread List Card Contract

## Overview

This document defines the unified contract for `thread_list` cards across all intents (followups, suspicious, unsubscribe, bills, interviews, clean_promos).

## Backend Contract

### Models (schemas_agent.py)

```python
class ThreadSummary(BaseModel):
    """Unified thread summary for thread_list cards."""
    thread_id: str = Field(..., alias="threadId")
    subject: str
    sender: str = Field(..., alias="from")
    snippet: Optional[str] = None
    last_seen_at: datetime = Field(..., alias="lastMessageAt")
    labels: List[str] = Field(default_factory=list)
    risk_score: Optional[int] = Field(None, alias="riskScore")
    is_unread: Optional[bool] = Field(None, alias="unreadCount")
    gmail_url: Optional[str] = Field(None, alias="gmailUrl")

class ThreadListCard(BaseModel):
    """Thread list card for Thread Viewer UI component."""
    kind: Literal["thread_list"]
    intent: str  # e.g. "followups", "unsubscribe", "suspicious"
    title: str
    time_window_days: Optional[int] = None
    mode: Literal["normal", "preview_only"] = "normal"
    threads: List[Dict[str, Any]]  # ThreadSummary objects as dicts
```

### Card Builder Helper (orchestrator.py)

```python
def _build_thread_cards(
    self,
    *,
    intent: str,
    title: str,
    summary_body_if_any: Optional[str],
    threads: List[Dict[str, Any]],
    time_window_days: int,
    preview_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Build both summary and thread_list cards using unified contract.

    Returns:
        - Summary card (followups_summary/generic_summary) with count
        - Thread list card (thread_list) only if threads is non-empty

    Guarantees:
    - No "multiple follow-ups" with count: 0
    - Thread viewer only appears when threads actually exist
    """
```

## Usage Per Intent

### 1. Followups

```python
cards = self._build_thread_cards(
    intent="followups",
    title=title,
    summary_body_if_any="You have multiple follow-ups awaiting your reply." if count > 1 else None,
    threads=thread_summaries,
    time_window_days=7,
    preview_only=True,
)
```

**Result when count > 0:**
- Card 1: `followups_summary` with body text
- Card 2: `thread_list` with `intent="followups"` and populated threads

**Result when count == 0:**
- Card 1: `followups_summary` with "all caught up" message
- No thread_list card

### 2. Suspicious

```python
cards = self._build_thread_cards(
    intent="suspicious",
    title=title,
    summary_body_if_any=f"{count} suspicious email{'s' if count != 1 else ''} found",
    threads=thread_summaries,
    time_window_days=30,
    preview_only=True,
)
```

### 3. Unsubscribe

```python
cards = self._build_thread_cards(
    intent="unsubscribe",
    title="Unsubscribe from Unopened Newsletters",
    summary_body_if_any=f"{count} newsletters found that haven't been opened in {time_window_days} days.",
    threads=thread_summaries,
    time_window_days=60,
    preview_only=True,
)
```

### 4. Bills

```python
cards = self._build_thread_cards(
    intent="bills",
    title=title,
    summary_body_if_any=f"{count} bill{'s' if count != 1 else ''} found",
    threads=thread_summaries,
    time_window_days=30,
    preview_only=True,
)
```

### 5. Interviews

```python
cards = self._build_thread_cards(
    intent="interviews",
    title=title,
    summary_body_if_any=f"{count} interview-related email{'s' if count != 1 else ''} found",
    threads=thread_summaries,
    time_window_days=30,
    preview_only=True,
)
```

### 6. Clean Promos

```python
cards = self._build_thread_cards(
    intent="clean_promos",
    title=title,
    summary_body_if_any=f"{count} promotional email{'s' if count != 1 else ''} found",
    threads=thread_summaries,
    time_window_days=30,
    preview_only=True,
)
```

## Frontend Integration

### TypeScript Types (types/agent.ts)

```typescript
export interface AgentCard {
  kind: AgentCardKind;
  title: string;
  body: string;
  email_ids: string[];
  meta: Record<string, any>;
  threads?: MailThreadSummary[];
  intent?: string; // For thread_list cards
}
```

### Rendering (AgentCardList.tsx)

```typescript
// thread_list cards are routed to ThreadListCard
if (card.kind === 'thread_list') {
  return <ThreadListCard key={`thread-list-${idx}`} card={card} />;
}
```

### ThreadListCard Component

```typescript
// Extract intent from card
const intent = card.intent ?? (card.meta?.intent as string) ?? 'generic';

// Render with intent-specific styling
<Badge
  variant="outline"
  className={cn(
    'text-xs',
    intent === 'suspicious' && 'border-red-400/30 text-red-400',
    intent === 'followups' && 'border-yellow-400/30 text-yellow-400',
    intent === 'bills' && 'border-blue-400/30 text-blue-400',
    intent === 'interviews' && 'border-purple-400/30 text-purple-400',
    intent === 'unsubscribe' && 'border-orange-400/30 text-orange-400',
    intent === 'clean_promos' && 'border-green-400/30 text-green-400'
  )}
>
  {intent}
</Badge>
```

## Testing

### Unit Tests (agentUi.test.ts)

```typescript
it('maps followups to summary + thread_list when threads exist', () => {
  const agentResult = {
    status: 'done',
    intent: 'followups',
    cards: [
      {
        kind: 'followups_summary',
        title: 'Conversations Waiting on Your Reply',
        body: 'You have multiple follow-ups awaiting your reply.',
        meta: { count: 2 },
      },
      {
        kind: 'thread_list',
        intent: 'followups',
        title: 'Conversations Waiting on Your Reply',
        threads: [...],
      },
    ],
  };

  const cards = mapAgentResultToCards(agentResult);
  expect(cards).toHaveLength(2);
  expect(cards[1].kind).toBe('thread_list');
  expect(cards[1].intent).toBe('followups');
});

it('returns only summary card when count is zero (no thread_list)', () => {
  const agentResult = {
    cards: [
      {
        kind: 'generic_summary',
        title: 'No Suspicious Emails Found',
        body: 'You\'re all caught up...',
        meta: { count: 0 },
      },
    ],
  };

  const cards = mapAgentResultToCards(agentResult);
  expect(cards).toHaveLength(1); // NO thread_list card!
});
```

## Key Guarantees

1. ✅ **Truthful counts**: `count` in summary card matches actual thread count
2. ✅ **Conditional thread viewer**: `thread_list` card only appears when `count > 0`
3. ✅ **Unified contract**: All intents use same `_build_thread_cards()` helper
4. ✅ **Intent-specific styling**: ThreadViewer shows badges based on intent
5. ✅ **Zero-state messaging**: Empty results show "all caught up" message
6. ✅ **Backwards compatible**: Fallback to `meta.intent` for legacy cards

## Manual Testing Checklist

For each intent button on `/chat`:

- [ ] **Follow-ups** → Click → Verify summary + thread_list cards when emails found
- [ ] **Suspicious** → Click → Verify summary + thread_list cards when risky emails found
- [ ] **Unsubscribe** → Click → Verify summary + thread_list cards when newsletters found
- [ ] **Bills Due** → Click → Verify summary + thread_list cards when bills found
- [ ] **Clean Promos** → Click → Verify summary + thread_list cards when promos found
- [ ] **Find Interviews** → Click → Verify summary + thread_list cards when interviews found

For zero-count scenarios:

- [ ] Verify only summary card appears (no thread_list)
- [ ] Verify summary body says "all caught up" or equivalent
- [ ] Verify count in meta is 0

## Migration Notes

### Changed Files

**Backend:**
- `services/api/app/schemas_agent.py`: Added `ThreadSummary`, `ThreadListCard` models, added `intent` field to `AgentCard`
- `services/api/app/agent/orchestrator.py`: Added `_build_thread_cards()`, `_build_thread_summary()`, `_group_emails_by_thread()` helpers, refactored `_build_cards_from_spec()` for all intents

**Frontend:**
- `apps/web/src/types/agent.ts`: Added `intent?: string` to `AgentCard`
- `apps/web/src/components/mail/ThreadListCard.tsx`: Updated to read `card.intent`
- `apps/web/src/lib/agentUi.test.ts`: Added 3 new tests for thread_list contract

### Breaking Changes

None! The changes are backwards compatible:
- Old cards without `intent` field will fallback to `meta.intent` or `'generic'`
- Summary cards (followups_summary, generic_summary) continue to work
- Thread list cards now consistently appear only when data exists
