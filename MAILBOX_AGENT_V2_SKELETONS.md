# Mailbox Agent v2 - Code Skeletons Created ✅

## What Was Created

### Backend Files

1. **`services/api/app/schemas_agent.py`** - Pydantic schemas ✅
   - `AgentRunRequest/Response` - Core contract
   - Tool parameter schemas (`EmailSearchParams`, `SecurityScanParams`, etc.)
   - Tool result schemas (`EmailSearchResult`, `SecurityScanResult`, etc.)
   - Redis cache schemas (`DomainRiskCache`, `ChatSessionCache`)
   - RAG schemas (`RAGContext`, `KnowledgeBaseEntry`)

2. **`services/api/app/agent/`** directory ✅
   - `__init__.py` - Module exports
   - `orchestrator.py` - `MailboxAgentOrchestrator` with intent classification, tool planning, execution
   - `tools.py` - `ToolRegistry` with 5 core tools (email_search, thread_detail, security_scan, applications_lookup, profile_stats)
   - `metrics.py` - Prometheus metrics (agent_runs_total, agent_tool_calls_total, etc.)
   - `redis_cache.py` - Domain risk + session caching with fallbacks
   - `rag.py` - RAG retrieval + synthesis (Phase 3)

3. **`services/api/app/routers/agent.py`** - API router ✅
   - `POST /agent/mailbox/run` - Execute agent run
   - `GET /agent/mailbox/run/{run_id}` - Get run status (stub, not implemented)
   - `GET /agent/tools` - List available tools
   - `GET /agent/health` - Health check

### Frontend Files

4. **`apps/web/src/types/agent.ts`** - TypeScript types ✅
   - Mirrors all Pydantic schemas
   - `AgentRunRequest/Response`, `AgentCard`, `ToolResult`, etc.

5. **`apps/web/src/api/agent.ts`** - API client ✅
   - `runMailboxAgent()` - Execute agent run
   - `getAgentRun()` - Get run by ID
   - `listAgentTools()` - List tools
   - `getAgentHealth()` - Health check
   - `buildAgentRequest()` - Helper to build request from chat query

### Documentation

6. **`MAILBOX_AGENT_V2.md`** - Complete implementation plan ✅
   - All 5 phases documented
   - Copy-paste checklist
   - Current assistant context

7. **`MAILBOX_AGENT_V2_SKELETONS.md`** - This file ✅

---

## Current Assistant Implementation

Your current chat assistant is in:
- **`services/api/app/routers/assistant.py`**
  - `/assistant/query` endpoint
  - Uses `AssistantQueryRequest/Response` schemas
  - Has intent classification, ES queries, LLM synthesis

---

## Next Steps to Implement Phase 1

### Step 1: Wire Agent Router into FastAPI

Add to `services/api/app/main.py`:

```python
from app.routers import agent  # Add this import

# ... existing router imports ...

# Add agent router (after assistant router)
app.include_router(agent.router)  # /agent/*
```

### Step 2: Add CSRF Exemptions

Add to `services/api/app/core/csrf.py`:

```python
CSRF_EXEMPT_ROUTES = [
    # ... existing routes ...
    "/agent/mailbox/run",  # Agent v2
    "/agent/tools",
    "/agent/health",
]
```

### Step 3: Implement `email_search` Tool

In `services/api/app/agent/tools.py`, replace the stub `_email_search()` with actual ES query:

```python
async def _email_search(self, params: Dict[str, Any], user_id: str) -> ToolResult:
    try:
        search_params = EmailSearchParams(**params)

        # Build ES query
        es_query = build_es_query(
            query_text=search_params.query_text,
            time_window_days=search_params.time_window_days,
            labels=search_params.labels,
            risk_min=search_params.risk_min,
        )

        # Execute ES search
        es_client = get_es_client()
        result = await es_client.search(
            index="gmail_emails",  # Or from config
            body=es_query,
            size=search_params.max_results,
        )

        # Parse hits
        emails = [hit["_source"] for hit in result["hits"]["hits"]]
        total = result["hits"]["total"]["value"]

        summary = f"Found {total} emails"
        if total == 0:
            summary = f"No emails found matching '{search_params.query_text}'"

        return ToolResult(
            tool_name="email_search",
            status="success",
            summary=summary,
            data=EmailSearchResult(
                emails=emails,
                total_found=total,
                query_used=search_params.query_text,
                filters_applied=search_params.dict(),
            ).dict(),
        )

    except Exception as e:
        logger.error(f"email_search failed: {e}", exc_info=True)
        return ToolResult(
            tool_name="email_search",
            status="error",
            summary="Email search failed",
            error_message=str(e),
        )
```

### Step 4: Test Agent Endpoint

```bash
# Start API server
cd services/api
python -m uvicorn app.main:app --reload --port 8000

# Test agent endpoint
curl -X POST http://localhost:8000/agent/mailbox/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show suspicious emails from this week",
    "user_id": "test@gmail.com",
    "mode": "preview_only",
    "context": {
      "time_window_days": 7,
      "filters": {"risk_min": 80}
    }
  }'
```

### Step 5: Update Frontend Chat Component

In `apps/web/src/pages/MailChat.tsx`:

```typescript
import { runMailboxAgent, buildAgentRequest } from '@/api/agent';
import type { AgentRunResponse } from '@/types/agent';

// When user sends a message:
async function handleSendMessage(query: string) {
  setBusy(true);

  try {
    const request = buildAgentRequest(query, user.email, {
      timeWindowDays: 30,
      filters: { labels: ["INBOX"] },
    });

    const response: AgentRunResponse = await runMailboxAgent(request);

    // Render response
    setMessages(prev => [
      ...prev,
      {
        role: 'assistant',
        content: response.answer,
        cards: response.cards,
        tools_used: response.tools_used,
        metrics: response.metrics,
      },
    ]);

  } catch (error) {
    console.error('Agent run failed:', error);
    // Show error card
  } finally {
    setBusy(false);
  }
}
```

### Step 6: Add Feature Flag

In `.env.production`:
```bash
VITE_CHAT_AGENT_V2=0  # Disabled by default
```

In code:
```typescript
const useAgentV2 = import.meta.env.VITE_CHAT_AGENT_V2 === '1';

if (useAgentV2) {
  // Use new agent
  const response = await runMailboxAgent(request);
} else {
  // Use legacy assistant
  const response = await assistantQuery(payload);
}
```

---

## Phase 1 Completion Checklist

- [ ] Wire agent router into FastAPI (`main.py`)
- [ ] Add CSRF exemptions for `/agent/*` endpoints
- [ ] Implement `email_search` tool with real ES queries
- [ ] Test `POST /agent/mailbox/run` endpoint
- [ ] Update `MailChat.tsx` to use agent v2 API
- [ ] Add feature flag `VITE_CHAT_AGENT_V2`
- [ ] Test chat UI with agent v2
- [ ] Implement remaining tools:
  - [ ] `thread_detail` (DB query for full thread)
  - [ ] `security_scan` (call EmailRiskAnalyzer)
  - [ ] `applications_lookup` (map emails → jobs)
  - [ ] `profile_stats` (inbox analytics)
- [ ] Add E2E tests for agent endpoints
- [ ] Deploy to dev environment for testing

---

## Phase 2 - Redis Caching (After Phase 1)

- [ ] Ensure Redis is configured (`REDIS_URL` in `.env`)
- [ ] Test Redis connectivity with `GET /agent/health`
- [ ] Implement domain risk caching in `security_scan` tool
- [ ] Implement session context caching for follow-up queries
- [ ] Add Redis fallback logic (graceful degradation)
- [ ] Monitor Redis metrics in Grafana

---

## Phase 3 - RAG (After Phase 2)

- [ ] Create knowledge base table in Postgres
- [ ] Seed KB with phishing patterns + job search docs
- [ ] Implement `retrieve_email_contexts()` in `rag.py`
- [ ] Implement `retrieve_kb_contexts()` in `rag.py`
- [ ] Wire RAG into orchestrator (use contexts in LLM synthesis)
- [ ] Add RAG metrics to Prometheus
- [ ] Test RAG fallback modes

---

## Quick Test Commands

```bash
# Backend - Test tools endpoint
curl http://localhost:8000/agent/tools | jq

# Backend - Test health
curl http://localhost:8000/agent/health | jq

# Backend - Run agent
curl -X POST http://localhost:8000/agent/mailbox/run \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "query": "Show suspicious emails",
  "user_id": "test@example.com",
  "mode": "preview_only"
}
EOF

# Frontend - Build and test
cd apps/web
npm run dev
# Open http://localhost:5173/chat
# Send message: "Show suspicious emails from this week"
```

---

## Questions?

If you need help with:
1. **ES query implementation** → I can draft the exact ES query for `email_search`
2. **DB queries for tools** → I can show how to query Postgres for `thread_detail`
3. **Frontend card rendering** → I can draft `AgentCardRenderer.tsx` component
4. **Prometheus dashboard** → I can create Grafana dashboard JSON for agent metrics

Just ask!
