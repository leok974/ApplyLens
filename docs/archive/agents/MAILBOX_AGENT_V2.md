# Mailbox Agent v2 - Implementation Plan

## 🎯 Goals

1. **Always-contextual**: Every answer pulls from real inbox data (ES, DB), not hardcoded text.
2. **Security-aware by default**: Agent automatically checks domains/risk signals when talking about legitimacy or "is this phishing?".
3. **RAG-powered**: Can synthesize answers from:
   - Your own emails (threads, conversations, recruiter chains)
   - A small curated knowledge base (phishing patterns, job search best practices, ApplyLens FAQ)
4. **Resilient**: Graceful fallbacks if ES, Redis, or RAG components fail.
5. **Observable**: All runs and tool calls show up in Prometheus/Grafana so you can see how the agent behaves in prod.

---

## 🧱 Phase 0 – Inventory & Contracts

### 0.1. Confirm current pieces

**Backend:**
- `/search`, `/emails`, `/security/*`, `/policy/security`, `/applications/*`, `/gmail/status`, etc.
- `EmailRiskAnalyzer` + `emails.risk_score`, `emails.flags`, `emails.quarantined`
- Redis already available via `REDIS_URL` (but mostly unused)
- Elasticsearch index with good analyzers for subject/body, labels, recency

**Frontend:**
- Chat page (`/chat`) with tools like "Suspicious" / "Bills Due" etc., currently using stubbed tools

**Telemetry:**
- HTTP metrics, backfill metrics, security metrics, Grafana dashboards

### 0.2. Define a stable "Agent run" contract

Single JSON shape used everywhere (backend, frontend, telemetry):

```json
{
  "run_id": "uuid",
  "user_id": "gmail-account-id",
  "query": "Show suspicious emails from new domains this week",
  "mode": "preview_only | apply_actions",
  "context": {
    "time_window_days": 30,
    "filters": { "labels": ["INBOX"], "risk_min": 80 }
  },
  "answer": "…",
  "cards": [ /* typed tool results */ ],
  "tools_used": ["email_search", "domain_risk", "rag_knowledge"],
  "metrics": {
    "emails_scanned": 37,
    "tool_calls": 4,
    "rag_sources": 3,
    "duration_ms": 850
  }
}
```

We'll anchor everything else on this.

---

## 🧰 Phase 1 – Real Tool Layer (no RAG yet)

Replace stubs with a small tool registry that the agent calls.

### 1.1. Core tools

- **`email_search`**: Query ES for top N threads/emails given a natural-language query + filters (time window, labels)
- **`thread_detail`**: Pull full thread from Postgres (headers, body, risk_score, flags)
- **`security_scan`**: Call your existing `EmailRiskAnalyzer` / `/security/rescan` for specific email IDs
- **`applications_lookup`**: Map emails → job applications (`/applications/from-email` style logic)
- **`profile_stats`**: Use existing `/emails/stats` / analytics endpoint for "what's my inbox like?" questions

Each tool returns a typed payload (for cards) and a short, LLM-friendly summary string.

### 1.2. Orchestrator

Implement a `MailboxAgentOrchestrator` that:

1. Parses the user query (intent classification: "suspicious", "bills", "follow-ups", "find interviews", generic)
2. Chooses a tool plan (sequence of tools with parameters)
3. Executes the tools (with timeouts)
4. Asks the LLM: "Given query + tool results, write answer + decide which cards to show."

### 1.3. Fallbacks (before RAG)

- If ES fails → use Postgres simple search or say "I can't search right now, but…"
- If security API fails → fall back to `emails.risk_score` already stored; or a safe generic message
- If orchestrator errors → return a single "system error" card + log to Prometheus

---

## 🧠 Phase 2 – Redis-backed Domain & Session Intelligence

Use Redis for fast, cached intelligence rather than recomputing or hitting external APIs every time.

### 2.1. Domain risk cache

**Key design:**
```
Key: domain_risk:{domain}
Value: JSON { risk_score, first_seen_at, last_seen_at, email_count, flags, evidence }
TTL: e.g. 7–30 days (refresh on use)
```

**Flow:**

When scanning or answering anything about "is this email legit?":

1. Extract domain(s) from sender, links
2. Check Redis cache:
   - **Hit** → use risk info directly
   - **Miss** → run `EmailRiskAnalyzer` signals (DMARC/SPF, new-domain, suspicious TLD, URL mismatch)
   - Store result in Redis
3. Optionally log "new_domain_seen" events to Postgres for analytics

### 2.2. Chat session context cache

```
Key: chat:session:{user_id}
Value: small JSON like { last_query, pinned_thread_ids, last_time_window }
```

Lets agent interpret follow-ups ("what about this week?") without the frontend re-sending the full context.

### 2.3. Fallbacks

If Redis is down:
- Domain risk falls back to DB-only heuristics
- Chat still works; just less "smart" with follow-ups
- All Redis calls wrapped with short timeouts + swallow errors (log + metric, never crash agent)

---

## 📚 Phase 3 – RAG for Inbox + Knowledge

Make the agent actually "read" relevant emails/docs instead of hallucinating.

### 3.1. Retrieval sources

**Inbox RAG (per-user)**
- Use ES as the primary retriever:
  - For a query, fetch top ~20 relevant emails or threads
  - Filter by time window + labels if present
  - For v1, you can keep this purely BM25 (no vectors) and still call it "RAG"

**Global knowledge base**
- New table/index for curated docs:
  - Phishing examples + patterns
  - Job search best practices
  - ApplyLens UX tips ("how do I use X?")
- Store in Postgres + ES (or a small pgvector index later)
- Simple ingestion script to add markdown files

### 3.2. RAG pipeline

For each agent run, when needed:

1. **Build two queries:**
   - A semantic search query over emails: "suspicious new domains" / "follow-ups due" / etc.
   - A knowledge query: "phishing signs of fake recruiter emails"

2. **Retrieve:**
   - ES: top N emails (`email_contexts`)
   - Knowledge index: top M docs (`kb_contexts`)

3. **Ask the LLM:**
   - "Given the user query and these email snippets and KB docs, answer + highlight which emails you're basing it on."

### 3.3. Fallback modes

- If ES works but KB fails → only use email contexts, mention you're using inbox only
- If both fail → agent replies with a "I can't fetch your emails right now, but general advice is…" answer (hardcoded safe text)
- If LLM times out → provide a short templated response and attach raw cards (emails list)

---

## 📊 Phase 4 – Telemetry & Guardrails

Wire everything into your existing Prometheus/Grafana stack.

### 4.1. Metrics

Add Prometheus metrics in the API:

```python
agent_runs_total{intent, mode, status}
# (status = success|tool_error|llm_error|timeout|validation_error)

agent_tool_calls_total{tool, status}

agent_tool_latency_ms_bucket{tool}  # histogram

agent_rag_context_count{source="emails|kb"}

agent_redis_hits_total{type="domain|session", result="hit|miss|error"}

agent_security_checks_total{result="safe|risky|quarantined"}
```

### 4.2. Dashboards

In Grafana - "Mailbox Agent" dashboard:
- Runs per minute/hour
- Success vs error rate
- Tool usage breakdown
- RAG context counts
- Top intents (suspicious, bills, follow-ups, etc.)

**Alert rules:**
- High error rate for `agent_runs_total` (>X% over 5–15min)
- Spike in `agent_security_checks_total{result="risky"}` → security alert

### 4.3. Safety guardrails

**Modes:**
- `preview_only`: Agent never auto-applies actions; only suggests (default)
- `apply_actions`: Must require explicit user confirmation in UI

**For legitimacy/phishing questions:**
- Always run security + domain tools
- If anything fails, respond conservatively ("I can't fully verify this; here's what I can say safely…")

---

## 🧪 Phase 5 – Frontend Wiring & Tests

### 5.1. Chat UI

Update chat page to treat each question as an `AgentRun` object (the JSON shape from Phase 0).

**Render:**
- User bubble (query)
- Single "thinking" bubble while `status=running`
- Assistant answer + cards when `status=done`

**Add an "Understanding used" collapsible section:**
- Show which tools were invoked, counts, maybe "N emails scanned"

### 5.2. E2E tests

**Playwright tests for prod/dev:**

**`chat-suspicious-basic.spec.ts`:**
- Ask: "Show suspicious emails from new domains this week and explain why."
- Assert:
  - At least one tool card is rendered (or explicit "none found" card)
  - No duplicate sentences

**`chat-rag-fallbacks.spec.ts` (dev only):**
- Mock ES failure → agent still returns safe message with error card
- Mock Redis failure → agent works without caching

---

## 📌 Implementation Order (Copy-Paste Checklist)

- [ ] **Phase 0**: Define `AgentRun` schema (Pydantic + TS types)
- [ ] **Phase 1.1**: Implement tool registry (`email_search`, `thread_detail`, `security_scan`, `applications_lookup`, `profile_stats`)
- [ ] **Phase 1.2**: Build `MailboxAgentOrchestrator` with simple rule-based planner + LLM summarizer
- [ ] **Phase 1.3**: Add fallback logic for tool failures
- [ ] **Phase 2.1**: Introduce Redis `domain_risk` cache; wrap with fallbacks
- [ ] **Phase 2.2**: Add Redis `chat:session` state cache
- [ ] **Phase 3.1**: Stand up basic RAG:
  - [ ] ES-based retrieval for emails
  - [ ] Small KB index for security + job search docs
- [ ] **Phase 3.2**: Build RAG pipeline with LLM synthesis
- [ ] **Phase 3.3**: Add RAG fallback modes
- [ ] **Phase 4.1**: Add Prometheus metrics for agent
- [ ] **Phase 4.2**: Create Grafana dashboard + alerts
- [ ] **Phase 4.3**: Implement safety guardrails
- [ ] **Phase 5.1**: Wire agent endpoint: `POST /agent/mailbox/run`
- [ ] **Phase 5.2**: Update frontend `/chat` to use `AgentRun` + clean thinking bubble behavior
- [ ] **Phase 5.3**: Write Playwright tests for chat happy-path + fallbacks
- [ ] **Phase 5.4**: Gradual rollout: dev → staging → prod with feature flag `VITE_CHAT_AGENT_V2`

---

## 🔍 Next Steps - Code Skeletons Needed

To start implementation, provide skeletons for:

### Backend Files

**1. `services/api/app/schemas_agent.py`** - Pydantic schemas:
```python
# AgentRun request/response models
# AgentContext, AgentMode, ToolResult, AgentCard schemas
```

**2. `services/api/app/agent/` directory structure:**
```
agent/
├── __init__.py
├── orchestrator.py       # MailboxAgentOrchestrator
├── tools.py              # Tool registry + implementations
├── redis_cache.py        # Domain risk + session caching
├── rag.py                # RAG retrieval + synthesis
└── metrics.py            # Prometheus metrics
```

**3. `services/api/app/routers/agent.py`** - New router:
```python
# POST /agent/mailbox/run
# GET /agent/mailbox/run/{run_id}
# GET /agent/tools (list available tools)
```

### Frontend Files

**4. `apps/web/src/types/agent.ts`** - TypeScript types:
```typescript
// AgentRun, AgentCard, AgentMetrics interfaces
```

**5. `apps/web/src/api/agent.ts`** - API client:
```typescript
// runMailboxAgent(), getAgentRun(), listTools()
```

**6. Update `apps/web/src/pages/MailChat.tsx`**:
```typescript
// Use AgentRun contract
// Single thinking indicator
// Render tools_used section
```

### Current Backend Context Needed

Please identify the current file that handles chat stubs:
- Is it `app/routers/assistant.py`?
- `app/mailbox_assistant.py`?
- Something else?

Once you provide this, I'll draft the exact Pydantic models + endpoint skeleton for `/agent/mailbox/run` that matches this plan.
