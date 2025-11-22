# Agent v2 - Production Deployment Summary

**Deployment Date:** November 19, 2025
**Version:** 0.5.3
**Status:** ✅ PRODUCTION READY

---

## 🎯 What Was Deployed

### Core Features
- **Structured LLM Answering**: Ollama (primary) → OpenAI (fallback) with JSON enforcement
- **Email Search Tool**: AsyncElasticsearch BM25 queries with user_id, time, label, risk filters
- **Security Scan Tool**: Domain risk analysis with Redis caching (30d TTL)
- **RAG Module**: Email + Knowledge Base context retrieval for LLM synthesis
- **Prometheus Metrics**: 8 metrics with `mailbox_agent_*` namespace
- **CSRF Exemptions**: `/agent/*` routes exempt for API testing

### Tool Status
- ✅ `email_search` - Fully implemented with ES queries
- ✅ `security_scan` - Risk analysis with Redis cache
- 🚧 `thread_detail` - Stub (DB query pending)
- 🚧 `applications_lookup` - Stub (DB query pending)
- 🚧 `profile_stats` - Stub (DB query pending)

---

## 🔧 Critical Fixes Applied

### 1. Elasticsearch User ID Issue
**Problem:** Emails had no `user_id` field
**Solution:** Added `user_id=leoklemet.pa@gmail.com` to all 4909 documents via update_by_query
**Impact:** Agent can now query user-specific emails

### 2. ES Query Type Mismatch
**Problem:** Using `term` query on analyzed text field
**Solution:** Changed to `match` query for `user_id` filter
**Impact:** Queries now return results (4909 total, 216 in last 7 days)

### 3. Aggressive Default Filters
**Problem:** `EmailSearchParams` defaulted to `labels: ["INBOX"]` and orchestrator added `risk_min: 80`
**Solution:** Removed INBOX default, removed risk_min from orchestrator
**Impact:** Generic queries now return all emails, security_scan categorizes by risk

### 4. RAGContext Schema Mismatch
**Problem:** Code accessed `ctx.source` and `ctx.id` but schema had `source_type` and `source_id`
**Solution:** Updated `answering.py` to use correct field names
**Impact:** RAG retrieval works, 3 KB contexts returned

### 5. AsyncElasticsearch Dependency
**Problem:** Missing `aiohttp` for AsyncElasticsearch
**Solution:** Added to `pyproject.toml`
**Impact:** RAG and email_search use async ES client

### 6. DomainRiskCache Type Error
**Problem:** Passing plain dict to `set_domain_risk()` expecting Pydantic model
**Solution:** Create `DomainRiskCache` model with proper fields
**Impact:** Redis caching works, security_scan completes successfully

### 7. Network Connectivity (Earlier Phase)
**Problem:** API couldn't reach ES at `http://es:9200`
**Solution:** Added `aliases: - es` to elasticsearch in docker-compose.prod.yml
**Impact:** All containers can reach ES

---

## 📊 Test Results

### Test Query: "Show suspicious emails from this week"
**User:** leoklemet.pa@gmail.com
**Time Window:** 7 days

**Results:**
```json
{
  "status": "done",
  "answer": "There is one suspicious email identified this week...",
  "cards": [
    {
      "kind": "suspicious_summary",
      "title": "Suspicious Email Found",
      "body": "1 email flagged as risky this week.",
      "meta": { "count": 1, "time_window_days": 7 }
    }
  ],
  "tools_used": ["email_search", "security_scan"],
  "metrics": {
    "emails_scanned": 50,
    "tool_calls": 2,
    "rag_sources": 3,
    "duration_ms": 11260,
    "llm_used": "ollama"
  }
}
```

### Database Stats
- **Total Emails:** 4909
- **Last 7 Days:** 216 emails
- **Last 30 Days:** 1585 emails
- **Latest Email:** 2025-11-19T01:40:44

---

## 🚀 Production Endpoints

### Agent Run
```bash
POST http://localhost:8003/agent/mailbox/run
Content-Type: application/json

{
  "query": "Show suspicious emails from this week",
  "user_id": "leoklemet.pa@gmail.com",
  "mode": "preview_only",
  "context": {
    "time_window_days": 7,
    "filters": {}
  }
}
```

### Tool Registry
```bash
GET http://localhost:8003/agent/tools
```

### Health Check
```bash
GET http://localhost:8003/agent/health
```

---

## 📦 Container Status

```bash
applylens-es-prod      Running, Healthy ✅
applylens-redis-prod   Running, Healthy ✅
applylens-db-prod      Running, Healthy ✅
applylens-api-prod     Running, Healthy ✅ (leoklemet/applylens-api:0.5.3)
```

---

## 🔄 Next Steps

### Phase 1.1 - Complete Remaining Tools
- [ ] Implement `thread_detail` (fetch from Postgres)
- [ ] Implement `applications_lookup` (map emails → job applications)
- [ ] Implement `profile_stats` (inbox analytics)

### Phase 1.2 - Knowledge Base
- [ ] Seed `agent_kb` ES index: `python scripts/seed_agent_kb.py`
- [ ] Add phishing patterns, job search tips, ApplyLens FAQ

### Phase 1.3 - Frontend Integration
- [ ] Update `apps/web/src/types/agent.ts` with schemas
- [ ] Wire chat component to `/agent/mailbox/run`
- [ ] Render AgentCard components
- [ ] Add Playwright E2E tests

### Phase 1.4 - Monitoring
- [ ] Create Grafana dashboard for `mailbox_agent_*` metrics
- [ ] Set up alerts for error rates, latency

### Phase 2 - Advanced Features
- [ ] Email actions (label, archive, reply)
- [ ] Multi-turn conversations (session context)
- [ ] Bulk operations
- [ ] Smart scheduling/reminders

---

## 📝 Git Commits

**Branch:** `thread-viewer-v1`
**Commits pushed:** 10 commits
**Latest:** `afbe9aa` - "fix(agent): Fix DomainRiskCache model usage in security_scan"

**Key Commits:**
- `f91401b` - Fix RAGContext schema and AsyncES usage
- `b5a6314` - Use match query for user_id filter (analyzed field)
- `0b25d1b` - Remove default INBOX filter, add comprehensive logging
- `afbe9aa` - Fix DomainRiskCache model usage in security_scan

---

## ✅ Verification Checklist

- [x] Docker image built and pushed (0.5.3)
- [x] Container deployed and healthy
- [x] Agent endpoint responding
- [x] Email search returning results
- [x] Security scan categorizing by risk
- [x] LLM generating structured JSON
- [x] RAG retrieving contexts
- [x] Redis caching working
- [x] Metrics recorded
- [x] Git pushed to GitHub
- [x] Multiple query types tested

---

**Agent v2 is now live in production! 🎉**
