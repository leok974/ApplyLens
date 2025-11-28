# Agent v2 Frontend Integration Guide

## Overview
This guide covers integrating the Mailbox Agent v2 backend with the chat UI.

---

## 1. Feature Flag Setup

### Environment Variables
Add to `.env.production`:
```bash
VITE_CHAT_AGENT_V2=1  # Enable when ready for production
```

Add to `.env.development`:
```bash
VITE_CHAT_AGENT_V2=0  # Keep old behavior during development
```

### Config Usage
```typescript
// apps/web/src/config/features.ts
export const FEATURES = {
  chatAgentV2: import.meta.env.VITE_CHAT_AGENT_V2 === '1',
  // ... other flags
};
```

---

## 2. API Client

### Create Agent API Client
```typescript
// apps/web/src/api/agent.ts
import type {
  AgentRunRequest,
  AgentRunResponse,
  AgentCard,
} from '@/types/agent';

export async function runAgent(
  request: AgentRunRequest
): Promise<AgentRunResponse> {
  const response = await fetch('/agent/mailbox/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
    credentials: 'include', // For session cookies
  });

  if (!response.ok) {
    throw new Error(`Agent run failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getAgentHealth(): Promise<{ status: string }> {
  const response = await fetch('/agent/health');
  return response.json();
}
```

### TypeScript Types
```typescript
// apps/web/src/types/agent.ts
export interface AgentRunRequest {
  query: string;
  mode: 'preview_only' | 'apply_actions';
  context: {
    time_window_days: number;
    filters?: Record<string, any>;
    session_id?: string | null;
  };
  user_id: string; // From auth context
}

export interface AgentRunResponse {
  run_id: string;
  user_id: string;
  query: string;
  mode: string;
  context: {
    time_window_days: number;
    filters: Record<string, any>;
    session_id: string | null;
  };
  status: 'running' | 'done' | 'error';
  answer: string;
  cards: AgentCard[];
  tools_used: string[];
  metrics: AgentMetrics;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface AgentCard {
  kind:
    | 'suspicious_summary'
    | 'bills_summary'
    | 'followups_summary'
    | 'interviews_summary'
    | 'generic_summary'
    | 'error';
  title: string;
  body: string;
  email_ids: string[];
  meta: Record<string, any>;
}

export interface AgentMetrics {
  emails_scanned: number;
  tool_calls: number;
  rag_sources: number;
  duration_ms: number;
  redis_hits: number;
  redis_misses: number;
  llm_used: string | null;
}
```

---

## 3. Chat UI Integration

### Update Chat Component
```typescript
// apps/web/src/pages/Chat.tsx
import { useState } from 'react';
import { runAgent } from '@/api/agent';
import { AgentCard } from '@/components/AgentCard';
import { FEATURES } from '@/config/features';
import { useAuth } from '@/hooks/useAuth';

export function Chat() {
  const { user } = useAuth();
  const [isThinking, setIsThinking] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const handleSendMessage = async (query: string) => {
    // Add user message
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: query, timestamp: new Date() },
    ]);

    if (FEATURES.chatAgentV2) {
      // Use Agent v2
      setIsThinking(true);
      try {
        const response = await runAgent({
          query,
          mode: 'preview_only',
          context: {
            time_window_days: 30, // Default, can be dynamic
          },
          user_id: user.email,
        });

        // Add agent response
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: response.answer,
            cards: response.cards,
            metrics: response.metrics,
            timestamp: new Date(response.completed_at || Date.now()),
          },
        ]);
      } catch (error) {
        // Error handling
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: 'Sorry, the agent is temporarily unavailable.',
            cards: [
              {
                kind: 'error',
                title: 'Agent Error',
                body: error.message,
                email_ids: [],
                meta: {},
              },
            ],
            timestamp: new Date(),
          },
        ]);
      } finally {
        setIsThinking(false);
      }
    } else {
      // Fallback to old chat behavior
      // ... existing code
    }
  };

  return (
    <div className="chat-container">
      {/* Messages */}
      {messages.map((msg, idx) => (
        <div key={idx} className="message" data-role={msg.role}>
          {msg.role === 'user' ? (
            <div className="user-message">{msg.content}</div>
          ) : (
            <div className="assistant-message">
              {/* Answer */}
              <div
                className="answer"
                data-testid="chat-assistant-answer"
              >
                {msg.content}
              </div>

              {/* Cards */}
              {msg.cards?.map((card, cardIdx) => (
                <AgentCard key={cardIdx} card={card} />
              ))}

              {/* Metrics hint */}
              {msg.metrics && (
                <div className="metrics-hint text-xs text-gray-500">
                  Based on {msg.metrics.emails_scanned} emails scanned
                  {msg.metrics.rag_sources > 0 &&
                    ` • ${msg.metrics.rag_sources} knowledge sources`}
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      {/* Thinking indicator */}
      {isThinking && (
        <div className="thinking-indicator" data-testid="chat-thinking">
          <div className="dots-animation">
            <span>•</span>
            <span>•</span>
            <span>•</span>
          </div>
          Thinking...
        </div>
      )}

      {/* Input */}
      <input
        placeholder="Ask your mailbox anything"
        onSubmit={handleSendMessage}
      />
    </div>
  );
}
```

---

## 4. Agent Card Component

```typescript
// apps/web/src/components/AgentCard.tsx
import type { AgentCard as AgentCardType } from '@/types/agent';
import {
  AlertTriangle,
  Receipt,
  Mail,
  Briefcase,
  FileText,
  XCircle,
} from 'lucide-react';

const CARD_ICONS = {
  suspicious_summary: AlertTriangle,
  bills_summary: Receipt,
  followups_summary: Mail,
  interviews_summary: Briefcase,
  generic_summary: FileText,
  error: XCircle,
};

const CARD_STYLES = {
  suspicious_summary: 'border-red-500 bg-red-50',
  bills_summary: 'border-blue-500 bg-blue-50',
  followups_summary: 'border-yellow-500 bg-yellow-50',
  interviews_summary: 'border-green-500 bg-green-50',
  generic_summary: 'border-gray-500 bg-gray-50',
  error: 'border-red-600 bg-red-100',
};

export function AgentCard({ card }: { card: AgentCardType }) {
  const Icon = CARD_ICONS[card.kind];
  const style = CARD_STYLES[card.kind];

  return (
    <div
      className={`agent-card border-l-4 p-4 rounded ${style}`}
      data-testid="agent-card"
      data-kind={card.kind}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-5 h-5" />
        <h3 className="font-semibold">{card.title}</h3>
        {card.meta?.count !== undefined && (
          <span className="ml-auto text-sm text-gray-600">
            {card.meta.count} items
          </span>
        )}
      </div>

      {/* Body */}
      <p className="text-sm text-gray-700">{card.body}</p>

      {/* Metadata */}
      {card.meta && (
        <div className="mt-2 flex gap-4 text-xs text-gray-500">
          {card.meta.time_window_days && (
            <span>Last {card.meta.time_window_days} days</span>
          )}
          {card.meta.mode && (
            <span className="capitalize">{card.meta.mode.replace('_', ' ')}</span>
          )}
        </div>
      )}

      {/* Email IDs (for future highlighting) */}
      {card.email_ids.length > 0 && (
        <div className="mt-2">
          <button
            className="text-xs text-blue-600 hover:underline"
            onClick={() => {
              // TODO: Highlight emails in inbox
              console.log('Show emails:', card.email_ids);
            }}
          >
            View {card.email_ids.length} email(s)
          </button>
        </div>
      )}
    </div>
  );
}
```

---

## 5. Empty & Error States

### Empty State (No Emails Scanned)
```typescript
{msg.metrics?.emails_scanned === 0 && (
  <div className="empty-state p-4 border rounded bg-yellow-50">
    <p className="text-sm text-gray-700">
      No emails matched this query or time window.
      <button
        className="ml-2 text-blue-600 hover:underline"
        onClick={() => {
          // Expand time window or adjust filters
        }}
      >
        Try widening the date range
      </button>
    </p>
  </div>
)}
```

### Error State (Agent Unavailable)
```typescript
catch (error) {
  if (error.message.includes('ES')) {
    // Elasticsearch down
    showNotification('Search temporarily unavailable', 'error');
  } else if (error.message.includes('Redis')) {
    // Redis down (caching degraded, but should still work)
    showNotification('Running with reduced performance', 'warning');
  } else {
    // Generic error
    showNotification('Agent temporarily unavailable', 'error');
  }
}
```

---

## 6. Playwright E2E Test

```typescript
// apps/web/tests/e2e/chat-agent-basic.spec.ts
import { test, expect } from '@playwright/test';

test.describe('@chat @agent basic functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Login (adjust based on your auth flow)
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'password');
    await page.click('button[type="submit"]');
    await page.waitForURL('/chat');
  });

  test('should show suspicious emails query', async ({ page }) => {
    // Send query
    await page
      .getByPlaceholder('Ask your mailbox anything')
      .fill('Show suspicious emails from this week');
    await page.getByRole('button', { name: 'Send' }).click();

    // Check thinking indicator
    const thinking = page.locator('[data-testid="chat-thinking"]');
    await expect(thinking).toBeVisible();

    // Wait for response
    await expect(thinking).not.toBeVisible({ timeout: 15000 });

    // Check answer
    const answer = page
      .locator('[data-testid="chat-assistant-answer"]')
      .last();
    await expect(answer).toContainText(/suspicious|email/i);

    // Check cards
    const cards = page.locator('[data-testid="agent-card"]');
    await expect(cards).toHaveCountGreaterThan(0);

    // Check card kind
    const firstCard = cards.first();
    await expect(firstCard).toHaveAttribute(
      'data-kind',
      /suspicious|generic|error/
    );
  });

  test('should handle generic recent emails query', async ({ page }) => {
    await page
      .getByPlaceholder('Ask your mailbox anything')
      .fill('Show my recent emails');
    await page.getByRole('button', { name: 'Send' }).click();

    await page.waitForSelector('[data-testid="chat-assistant-answer"]', {
      timeout: 15000,
    });

    const answer = page
      .locator('[data-testid="chat-assistant-answer"]')
      .last();
    await expect(answer).toContainText(/email|found|recent/i);

    // Should show metrics hint
    const metricsHint = page.locator('.metrics-hint').last();
    await expect(metricsHint).toContainText(/scanned/i);
  });

  test('should show error state on agent failure', async ({ page }) => {
    // Intercept and fail the agent request
    await page.route('**/agent/mailbox/run', (route) =>
      route.abort('failed')
    );

    await page
      .getByPlaceholder('Ask your mailbox anything')
      .fill('Test query');
    await page.getByRole('button', { name: 'Send' }).click();

    // Should show error card
    await page.waitForSelector('[data-kind="error"]', { timeout: 5000 });
    const errorCard = page.locator('[data-kind="error"]');
    await expect(errorCard).toBeVisible();
  });
});
```

---

## 7. Rollout Plan

### Phase 1: Internal Testing (1-2 days)
- [ ] Enable `VITE_CHAT_AGENT_V2=1` in dev environment
- [ ] Manual testing by team (10+ queries)
- [ ] Fix any UX issues discovered
- [ ] Run Playwright tests in CI

### Phase 2: Beta (3-5 days)
- [ ] Deploy to staging with feature flag
- [ ] Invite 5-10 beta users
- [ ] Monitor Grafana dashboards
- [ ] Collect feedback
- [ ] Fix critical bugs

### Phase 3: Production Rollout (gradual)
- [ ] Deploy to prod with `VITE_CHAT_AGENT_V2=0` (off by default)
- [ ] Enable for 10% of users (via A/B test)
- [ ] Monitor error rates, latency
- [ ] Increase to 50% if healthy
- [ ] Increase to 100% after 1 week

### Phase 4: Cleanup
- [ ] Remove old chat implementation
- [ ] Remove feature flag
- [ ] Update documentation

---

## 8. Monitoring & Alerts

### Grafana Dashboard Queries

**Panel 1: Agent Runs by Status**
```promql
sum by (status) (rate(mailbox_agent_runs_total[5m]))
```

**Panel 2: Tool Calls by Status**
```promql
sum by (tool, status) (rate(mailbox_agent_tool_calls_total[5m]))
```

**Panel 3: Redis Hit Rate**
```promql
sum by (result) (rate(mailbox_agent_redis_hits_total[5m]))
```

**Panel 4: RAG Context Volume**
```promql
sum by (source) (rate(mailbox_agent_rag_context_count[15m]))
```

**Panel 5: Agent Latency (p95)**
```promql
histogram_quantile(0.95, rate(mailbox_agent_run_duration_seconds_bucket[5m]))
```

### Alerts

**Alert 1: High Error Rate**
```yaml
- alert: AgentHighErrorRate
  expr: |
    sum(rate(mailbox_agent_runs_total{status="error"}[10m])) /
    sum(rate(mailbox_agent_runs_total[10m])) > 0.1
  for: 5m
  annotations:
    summary: Agent error rate > 10%
```

**Alert 2: Slow Agent Runs**
```yaml
- alert: AgentSlowRuns
  expr: |
    histogram_quantile(0.95,
      rate(mailbox_agent_run_duration_seconds_bucket[5m])
    ) > 15
  for: 10m
  annotations:
    summary: Agent p95 latency > 15s
```

---

## 9. Troubleshooting

### Common Issues

**Issue: "Agent temporarily unavailable"**
- Check: `curl http://localhost:8003/agent/health`
- Fix: Restart API container, check ES/Redis connectivity

**Issue: Empty email_ids in cards**
- Status: Known issue (low priority)
- Workaround: Users can still see count in meta
- Fix: Implement email_ids extraction in answering.py

**Issue: Ollama fallback to OpenAI**
- Check: Ollama container running?
- Impact: Higher latency (~2s more), OpenAI costs
- Fix: Restart Ollama or update OLLAMA_BASE env var

**Issue: emails_scanned=0**
- Check: ES index has documents? user_id field populated?
- Debug: Run test_search.py script
- Fix: Re-run user_id update_by_query

---

**Ready for frontend integration!** 🚀
