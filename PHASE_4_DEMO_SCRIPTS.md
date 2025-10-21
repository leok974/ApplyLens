# Phase 4 AI Features - Demo Scripts

This document provides curl commands to test all three Phase 4 AI features.

## Prerequisites

```bash
# 1. Start Ollama (local AI service)
ollama serve

# 2. Pull the model
ollama pull qwen2.5:7b-instruct

# 3. Set environment variables
export OLLAMA_BASE=http://localhost:11434
export OLLAMA_MODEL=qwen2.5:7b-instruct
export FEATURE_SUMMARIZE=true
export FEATURE_RAG_SEARCH=true

# 4. Start API server
cd services/api
uvicorn app.main:app --reload
```

---

## Feature 1: Email Summarizer

**Description:** Generates 5-bullet summary of email thread with citations.

### Health Check

```bash
curl http://localhost:8000/api/ai/health | jq
```

**Expected Output:**
```json
{
  "feature_enabled": true,
  "ollama_available": true,
  "ollama_base": "http://localhost:11434",
  "ollama_model": "qwen2.5:7b-instruct"
}
```

### Summarize Thread (Mock Data)

```bash
curl -X POST http://localhost:8000/api/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "demo-1",
    "max_citations": 3
  }' | jq
```

**Expected Output:**
```json
{
  "bullets": [
    "Bianca is scheduling an interview for a Software Engineer position",
    "Initial time proposed: Tuesday at 2 PM",
    "Hiring team confirmed Tuesday works",
    "Conflict arose on Bianca's side",
    "Rescheduled to Wednesday at 3 PM"
  ],
  "citations": [
    {
      "snippet": "Tuesday at 2 PM works perfectly for us",
      "message_id": "msg-002",
      "offset": 45
    },
    {
      "snippet": "Unfortunately a conflict has come up",
      "message_id": "msg-003",
      "offset": 12
    }
  ]
}
```

### Summarize Non-Existent Thread

```bash
curl -X POST http://localhost:8000/api/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "nonexistent",
    "max_citations": 3
  }' | jq
```

**Expected Output:**
```json
{
  "detail": "Thread not found: nonexistent"
}
```
*Status: 404*

---

## Feature 2: Smart Risk Badge

**Description:** Returns top 3 risk signals sorted by weight with explanations.

### Get Risk Signals (Requires Existing Email)

First, check if you have any emails in the database:

```bash
# List emails
curl http://localhost:8000/api/emails?limit=1 | jq '.items[0].id'
```

Then query risk signals:

```bash
# Replace EMAIL_ID with actual email ID
export EMAIL_ID="<email-id-from-above>"

curl "http://localhost:8000/api/security/risk-top3?message_id=$EMAIL_ID" | jq
```

**Expected Output (Example):**
```json
{
  "score": 45,
  "signals": [
    {
      "id": "DMARC_FAIL",
      "label": "DMARC Failed",
      "explain": "Message failed DMARC authentication check"
    },
    {
      "id": "SPF_FAIL",
      "label": "SPF Failed",
      "explain": "Sender IP not authorized by SPF record"
    },
    {
      "id": "NEW_DOMAIN",
      "label": "New Domain",
      "explain": "Sender domain registered recently"
    }
  ]
}
```

### Risk Check for Non-Existent Message

```bash
curl "http://localhost:8000/api/security/risk-top3?message_id=nonexistent" | jq
```

**Expected Output:**
```json
{
  "detail": "Message not found"
}
```
*Status: 404*

---

## Feature 3: RAG Search

**Description:** Semantic search across email corpus with highlighted snippets.

### Health Check

```bash
curl http://localhost:8000/api/rag/health | jq
```

**Expected Output (Mock Mode):**
```json
{
  "feature_enabled": true,
  "elasticsearch_available": false,
  "elasticsearch_host": "http://localhost:9200",
  "elasticsearch_index": "emails",
  "fallback_mode": "mock"
}
```

### Search Query (Mock Data)

```bash
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "q": "interview scheduling",
    "k": 5
  }' | jq
```

**Expected Output:**
```json
{
  "hits": [
    {
      "thread_id": "demo-1",
      "message_id": "msg-001",
      "score": 0.92,
      "highlights": [
        "...initial <em>interview</em> <em>scheduling</em> for next week...",
        "...prefer Tuesday or Wednesday afternoon..."
      ],
      "sender": "bianca@techcorp.com",
      "subject": "Interview Scheduling - Software Engineer Position",
      "date": "2025-01-14T09:00:00Z"
    },
    {
      "thread_id": "demo-1",
      "message_id": "msg-002",
      "score": 0.88,
      "highlights": [
        "...Tuesday at 2 PM works perfectly...",
        "...looking forward to the <em>interview</em>..."
      ],
      "sender": "hiring@startup.io",
      "subject": "Re: Interview Scheduling",
      "date": "2025-01-14T14:30:00Z"
    }
  ],
  "total": 3
}
```

### Search with Different k Value

```bash
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "q": "interview conflict",
    "k": 2
  }' | jq
```

### Search No Results

```bash
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "q": "nonexistent topic xyz",
    "k": 5
  }' | jq
```

**Expected Output:**
```json
{
  "hits": [],
  "total": 0
}
```

---

## Testing All Features Together

```bash
#!/bin/bash
# test_ai_features.sh - Test all Phase 4 AI features

echo "=== Testing AI Features ==="

echo -e "\n1. AI Summarizer Health"
curl -s http://localhost:8000/api/ai/health | jq '.ollama_available'

echo -e "\n2. Summarize Demo Thread"
curl -s -X POST http://localhost:8000/api/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "demo-1", "max_citations": 3}' \
  | jq '.bullets | length'

echo -e "\n3. RAG Health"
curl -s http://localhost:8000/api/rag/health | jq '.fallback_mode'

echo -e "\n4. RAG Search"
curl -s -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"q": "interview", "k": 3}' \
  | jq '.total'

echo -e "\n5. Risk Badge (needs email ID)"
EMAIL_ID=$(curl -s http://localhost:8000/api/emails?limit=1 | jq -r '.items[0].id')
if [ "$EMAIL_ID" != "null" ]; then
  curl -s "http://localhost:8000/api/security/risk-top3?message_id=$EMAIL_ID" \
    | jq '.score'
else
  echo "No emails found in database"
fi

echo -e "\n=== Tests Complete ==="
```

Make executable and run:

```bash
chmod +x test_ai_features.sh
./test_ai_features.sh
```

---

## Performance Benchmarks

### Summarizer

```bash
# Measure response time
time curl -X POST http://localhost:8000/api/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "demo-1"}' > /dev/null
```

**Expected:** <6s cold start, <2.5s cached

### Risk Badge

```bash
# Measure response time
EMAIL_ID="<some-email-id>"
time curl "http://localhost:8000/api/security/risk-top3?message_id=$EMAIL_ID" > /dev/null
```

**Expected:** <500ms (uses existing analyzer, no AI)

### RAG Search

```bash
# Measure response time
time curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"q": "interview", "k": 5}' > /dev/null
```

**Expected:** <100ms (mock), <2s (Elasticsearch)

---

## Feature Flags

Toggle features via environment variables:

```bash
# Disable summarizer
export FEATURE_SUMMARIZE=false

# Disable RAG search
export FEATURE_RAG_SEARCH=false

# Restart API server for changes to take effect
```

Test disabled state:

```bash
# Should return 503
curl -X POST http://localhost:8000/api/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "demo-1"}'
```

---

## Troubleshooting

### Ollama Not Running

```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# If not, start it
ollama serve
```

### Model Not Found

```bash
# List installed models
ollama list

# Pull model if missing
ollama pull qwen2.5:7b-instruct
```

### Elasticsearch Not Available

RAG search will automatically fall back to mock data. Check health:

```bash
curl http://localhost:8000/api/rag/health | jq '.fallback_mode'
# Should return "mock" if ES is unavailable
```

---

## Next Steps

1. **Frontend Integration:** Use the React components in `apps/web/src/components/`:
   - `SummaryCard.tsx` - Drop into email thread view
   - `RiskPopover.tsx` - Attach to email risk badge
   - `RagResults.tsx` - Add to search page

2. **E2E Testing:** See `PHASE_4_E2E_TESTS.md` for Playwright tests

3. **Demo Video:** Record workflow showing all three features in action

4. **Grafana Dashboard:** Add AI feature metrics (latency, usage, errors)
