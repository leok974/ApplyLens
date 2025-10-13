# Phase 5: Chat Assistant - Conversational Mailbox

**Date:** October 12, 2025  
**Status:** ✅ Implemented  
**Version:** 1.0

---

## Overview

Phase 5 transforms ApplyLens into a conversational mailbox assistant. Users can ask natural language questions about their emails and get intelligent responses powered by RAG (Retrieval-Augmented Generation), intent detection, and specialized mail tools.

### Key Features

✅ **8 Specialized Intents**

- Summarize, Find, Clean, Unsubscribe, Flag, Follow-up, Calendar, Task

✅ **Hybrid RAG Search**

- Keyword (BM25) + Semantic (vector) search over Elasticsearch

✅ **Smart Intent Detection**

- Rule-based pattern matching with fallback heuristics

✅ **Action Proposals**

- Non-destructive by default; can integrate with Phase 4 approval system

✅ **Citation Tracking**

- Every response cites source emails (subject, sender, date, ID)

✅ **Quick-Action Chips**

- Pre-configured queries for common tasks

✅ **Conversational UI**

- Dark-themed chat interface with message history

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │ ChatPage   │→ │ MailChat   │→ │ chatClient.ts          │ │
│  └────────────┘  └────────────┘  └────────────────────────┘ │
└────────────────────────────────┬────────────────────────────┘
                                 │ HTTP POST /api/chat
┌────────────────────────────────┴────────────────────────────┐
│                         Backend                              │
│  ┌────────────────┐                                          │
│  │  chat.py       │ POST /chat                               │
│  │  (Router)      │                                          │
│  └───────┬────────┘                                          │
│          │                                                    │
│          ├──→ intent.py  (Detect user intent)                │
│          │                                                    │
│          ├──→ rag.py     (Hybrid search: keyword + semantic) │
│          │    └──→ text.py  (Embeddings)                     │
│          │    └──→ Elasticsearch                             │
│          │                                                    │
│          ├──→ mail_tools.py                                  │
│          │    ├── summarize_emails()                         │
│          │    ├── find_emails()                              │
│          │    ├── clean_promos()                             │
│          │    ├── unsubscribe_inactive()                     │
│          │    ├── flag_suspicious()                          │
│          │    ├── follow_up()                                │
│          │    ├── create_calendar_events()                   │
│          │    └── create_tasks()                             │
│          │                                                    │
│          └──→ ChatResponse                                   │
│               ├── intent + explanation                       │
│               ├── answer (natural language)                  │
│               ├── actions (proposed)                         │
│               ├── citations (source emails)                  │
│               └── search_stats                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Backend Components

### 1. Intent Detection (`app/core/intent.py`)

**Rule-based pattern matching** to detect user intent from text.

**Supported Intents:**

- `summarize` - Provide concise bullet-point summary
- `find` - List specific emails with reasons
- `clean` - Propose archiving old promos
- `unsubscribe` - Propose unsubscribing from inactive newsletters
- `flag` - Surface suspicious/high-risk emails
- `follow-up` - Identify threads needing follow-up
- `calendar` - Create calendar event reminders
- `task` - Create tasks from actionable emails

**Example Patterns:**

```python
INTENTS = {
    "clean": [r"\bclean( up)?\b", r"\barchive\b", r"\bdeclutter\b"],
    "flag": [r"\b(suspicious|phish|scam|fraud|risk)\b"],
    "calendar": [r"\bcalendar\b", r"\bdue\b.*\b(date|before|by)\b"],
    # ... more patterns
}
```

**Fallback:** Defaults to `summarize` if no pattern matches.

### 2. RAG Search (`app/core/rag.py`)

**Hybrid keyword + semantic search** over Elasticsearch emails index.

**Features:**

- **Keyword Search:** Multi-field BM25 across subject, body, sender, labels
- **Semantic Search:** KNN vector search using embeddings (optional)
- **Structured Filters:** category, risk_score, sender_domain, date ranges, labels
- **Multi-tenant:** Supports user_id filtering

**Example Query:**

```python
rag_search(
    es,
    query="job applications from August",
    filters={
        "category": "jobs",
        "date_from": "2025-08-01",
        "date_to": "2025-08-31"
    },
    k=50
)
```

**Returns:**

```python
{
    "docs": [{"id": "...", "subject": "...", "sender": "...", ...}, ...],
    "total": 127,  # Total matching in ES
    "count": 50,   # Returned count
    "query": "job applications from August",
    "filters": {...}
}
```

### 3. Text Embeddings (`app/core/text.py`)

**Text-to-vector conversion** for semantic search.

**Current Implementation:**

- Deterministic random fallback (for development)
- Same text always produces same vector

**Future Integration:**

```python
# Option 1: OpenAI
from openai import OpenAI
client = OpenAI()
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=text
)
return response.data[0].embedding

# Option 2: Ollama (local)
import ollama
response = ollama.embeddings(
    model='nomic-embed-text',
    prompt=text
)
return response['embedding']
```

### 4. Mail Tools (`app/core/mail_tools.py`)

**8 specialized functions** that take RAG results and return `(answer, actions)` tuples.

#### `summarize_emails(rag, user_text)`

Returns concise bullet-point summary of top matching emails.

```
Found 127 emails. Top matches:
• [Interview confirmation] — recruiter@company.com — Oct 10, 2025 (#12345)
• [Application status] — hr@company.com — Oct 9, 2025 (#12346)
...
```

#### `find_emails(rag, user_text)`

Lists emails with match reasons (category, risk score, labels).

```
Found 45 matching emails:
• [Interview reminder] — recruiter@company.com — Oct 10, 2025
  → category: jobs | labels: interview
...
```

#### `clean_promos(rag, user_text)`

Proposes archiving old promotional emails (>7 days) with **exception handling**.

**Example:**

- Query: "Clean up promos older than a week unless they're from Best Buy"
- Extracts exception: "best buy"
- Filters out Best Buy emails before proposing archive actions

**Actions:**

```json
[
  {
    "action": "archive_email",
    "email_id": "12345",
    "params": {"reason": "Old promotional email", "category": "promo"}
  }
]
```

#### `unsubscribe_inactive(rag, user_text)`

Proposes unsubscribing from newsletters not engaged with in 60+ days.

**Heuristic:** Checks `received_at` age (in production, would check engagement metrics).

#### `flag_suspicious(rag, user_text)`

Surfaces high-risk emails from last 7 days with explanations.

```
⚠️ Found 3 suspicious emails this week:
• [Urgent: verify account] — noreply@suspicious.com — Oct 10, 2025
  → 🔴 Very high risk (95/100) | Possible phishing
...
```

#### `follow_up(rag, user_text)`

Identifies emails needing follow-up and suggests draft replies.

Looks for:

- `needs_reply` label
- `opportunity` category
- Keywords: "recruiter", "hiring", "interview"

#### `create_calendar_events(rag, user_text)`

Creates calendar reminders from emails.

**Date Extraction:**

- "before Friday" → calculates days until Friday
- "in 3 days" → adds 3 days from now
- Default: 3 days ahead

**Actions:**

```json
[
  {
    "action": "create_calendar_event",
    "email_id": "12345",
    "params": {
      "title": "Bill payment reminder",
      "when": "2025-10-15T12:00:00Z",
      "description": "Reminder from email: billing@company.com"
    }
  }
]
```

#### `create_tasks(rag, user_text)`

Creates tasks from actionable email content.

### 5. Chat Router (`app/routers/chat.py`)

**FastAPI router** providing 3 endpoints:

#### `POST /api/chat`

Main conversational endpoint.

**Request:**

```json
{
  "messages": [
    {"role": "user", "content": "What bills are due before Friday?"}
  ],
  "filters": {
    "category": "bills",
    "date_to": "2025-10-18"
  },
  "max_results": 50
}
```

**Response:**

```json
{
  "intent": "calendar",
  "intent_explanation": "Create calendar event reminders from email content",
  "answer": "📅 Prepared 3 calendar reminders for Friday, October 18:\n• [Electric bill due] — ...\n• [Credit card payment] — ...\n• [Internet bill] — ...",
  "actions": [
    {
      "action": "create_calendar_event",
      "email_id": "12345",
      "params": {"title": "Electric bill due", "when": "2025-10-18T12:00:00Z"}
    }
  ],
  "citations": [
    {"id": "12345", "subject": "Electric bill due", "sender": "billing@electric.com", "received_at": "2025-10-01T08:00:00Z"}
  ],
  "search_stats": {
    "total_results": 127,
    "returned_results": 3,
    "query": "What bills are due before Friday?",
    "filters": {"category": "bills"}
  }
}
```

#### `GET /api/chat/intents`

Lists all available intents with descriptions.

**Response:**

```json
{
  "summarize": {
    "patterns": ["\\bsummariz", "\\boverview\\b", ...],
    "description": "Summarize matching emails in a concise format"
  },
  "clean": {
    "patterns": ["\\bclean( up)?\\b", "\\barchive\\b", ...],
    "description": "Propose archiving old promotional emails"
  },
  ...
}
```

#### `GET /api/chat/health`

Health check endpoint.

---

## Frontend Components

### 1. Chat API Client (`lib/chatClient.ts`)

TypeScript client for chat API with type-safe interfaces.

**Functions:**

- `sendChatMessage(request)` - Send chat request
- `listIntents()` - Fetch available intents
- `chatHealth()` - Health check

**Types:**

```typescript
interface ChatRequest {
  messages: Message[]
  filters?: {
    category?: string
    risk_min?: number
    sender_domain?: string
    date_from?: string
    // ...
  }
  max_results?: number
}

interface ChatResponse {
  intent: string
  intent_explanation: string
  answer: string
  actions: ActionItem[]
  citations: Citation[]
  search_stats: {...}
}
```

### 2. MailChat Component (`components/MailChat.tsx`)

**Main chat interface** with:

- Quick-action chips (8 pre-configured queries)
- Message history (user/assistant bubbles)
- Input field with Enter-to-send
- Loading states (animated dots)
- Error handling
- Citation display
- Markdown-style formatting (**bold**, *italic*)

**Quick Actions:**

```typescript
const QUICK_ACTIONS = [
  {label: 'Summarize', text: 'Summarize recent emails about my job applications.', icon: '📧'},
  {label: 'Bills Due', text: 'What bills are due before Friday? Create calendar reminders.', icon: '💰'},
  {label: 'Clean Promos', text: 'Clean up promos older than a week unless they\'re from Best Buy.', icon: '🧹'},
  // ... 5 more
]
```

### 3. Chat Page (`pages/ChatPage.tsx`)

Simple page wrapper rendering `<MailChat />`.

### 4. Navigation

**Updated `AppHeader.tsx`:**

- Added "Chat" link in navigation menu
- Accessible at `/chat`

**Updated `App.tsx`:**

- Added `<Route path="/chat" element={<ChatPage />} />`

---

## Usage Examples

### Example 1: Summarize Recent Emails

**Query:**

```
Summarize recent emails about my job applications.
```

**Intent:** `summarize`

**Response:**

```
Found 23 emails. Top matches:
• [Interview invitation] — recruiter@tech.com — Oct 10, 2025 (#45678)
• [Application received] — hr@startup.com — Oct 9, 2025 (#45679)
• [Follow-up needed] — hiring@company.com — Oct 8, 2025 (#45680)
...

Sources:
• Interview invitation — recruiter@tech.com (Oct 10, 2025)
• Application received — hr@startup.com (Oct 9, 2025)
...
```

### Example 2: Bills with Calendar Reminders

**Query:**

```
What bills are due before Friday? Create calendar reminders.
```

**Intent:** `calendar`

**Response:**

```
*Create calendar event reminders from email content*

📅 Prepared 3 calendar reminders for Friday, October 18:
• [Electric bill due Oct 15] — billing@electric.com — Oct 1, 2025 (#12345)
• [Credit card payment due] — statements@bank.com — Oct 2, 2025 (#12346)
• [Internet service bill] — billing@isp.com — Oct 3, 2025 (#12347)

**3 actions proposed**

**Sources:**
• Electric bill due Oct 15 — billing@electric.com (Oct 1, 2025)
• Credit card payment due — statements@bank.com (Oct 2, 2025)
• Internet service bill — billing@isp.com (Oct 3, 2025)
```

### Example 3: Clean Promos with Exception

**Query:**

```
Clean up promos older than a week unless they're from Best Buy.
```

**Intent:** `clean`

**Response:**

```
Found 47 promotional emails older than a week (respecting exceptions: best buy). Proposing to archive 47.

**47 actions proposed**
```

**Actions:**

```json
[
  {"action": "archive_email", "email_id": "11111", "params": {"reason": "Old promotional email"}},
  {"action": "archive_email", "email_id": "11112", "params": {"reason": "Old promotional email"}},
  ...
]
```

### Example 4: Suspicious Emails

**Query:**

```
Show suspicious emails from new domains this week and explain why.
```

**Intent:** `flag`

**Response:**

```
⚠️ Found 2 suspicious emails this week:
• [Urgent: verify your account] — noreply@suspicious-domain.com — Oct 10, 2025 (#99999)
  → 🔴 Very high risk (95/100) | Suspicious category | Possible phishing
• [You've won a prize!] — winner@new-domain.net — Oct 9, 2025 (#99998)
  → 🟠 High risk (85/100) | Suspicious category

**Sources:**
• Urgent: verify your account — noreply@suspicious-domain.com (Oct 10, 2025)
• You've won a prize! — winner@new-domain.net (Oct 9, 2025)
```

### Example 5: Unsubscribe from Inactive Newsletters

**Query:**

```
Unsubscribe from newsletters I haven't opened in 60 days.
```

**Intent:** `unsubscribe`

**Response:**

```
Found 12 inactive newsletters. Proposing 12 unsubscribe actions.

Examples:
• [Daily Newsletter] — newsletter@example.com — Aug 1, 2025 (#77777)
• [Weekly Digest] — digest@another.com — Jul 28, 2025 (#77778)
• [Marketing Updates] — marketing@company.com — Jul 15, 2025 (#77779)

**12 actions proposed**
```

### Example 6: Find Specific Emails

**Query:**

```
Find interviews from August with confirmed times.
```

**Intent:** `find`

**Response:**

```
Found 5 matching emails:
• [Interview scheduled: Aug 15 at 2pm] — recruiter@tech.com — Aug 10, 2025
  → category: jobs | labels: interview
• [Confirmed: Video interview Aug 20] — hr@startup.com — Aug 12, 2025
  → category: jobs | labels: interview, confirmed
...
```

### Example 7: Follow-up Suggestions

**Query:**

```
Which recruiters haven't replied in 5 days? Draft follow-ups.
```

**Intent:** `follow-up`

**Response:**

```
💬 Emails needing follow-up:

• [Application for Senior Engineer] — recruiter@tech.com — Oct 5, 2025 (#55555)
  → Draft: "Hi,\n\nFollowing up on \"Application for Senior Engi...\n\nBest regards"

• [Interview thank you] — hr@company.com — Oct 4, 2025 (#55556)
  → Draft: "Hi,\n\nFollowing up on \"Interview thank you...\n\nBest regards"
```

### Example 8: Create Tasks

**Query:**

```
Create tasks from emails about pending action items.
```

**Intent:** `task`

**Response:**

```
✅ Prepared 4 tasks from emails:
• [Complete onboarding documents] — hr@company.com — Oct 10, 2025 (#88888)
• [Review contract terms] — legal@startup.com — Oct 9, 2025 (#88889)
• [Submit expense report] — finance@company.com — Oct 8, 2025 (#88890)
• [Schedule team meeting] — manager@company.com — Oct 7, 2025 (#88891)

**4 actions proposed**
```

---

## Integration with Phase 4

Phase 5 can be integrated with Phase 4 (Agentic Actions & Approval Loop) by **posting proposed actions to `/api/actions/propose`**.

**Modification in `chat.py`:**

```python
# After tool execution
if actions:
    # Extract email_ids from actions
    email_ids = [a["email_id"] for a in actions]
    
    # POST to Phase 4 propose endpoint
    # This creates ProposedAction records for approval
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8003/api/actions/propose",
            json={"email_ids": email_ids}
        )
    
    # Update answer to mention approval workflow
    answer += "\n\nℹ️ Actions sent to approval tray for review."
```

This allows users to:

1. Ask chat assistant for recommendations
2. Review proposed actions in Actions Tray
3. Approve, reject, or create policies ("Always do this")

---

## Testing

### Backend Tests (`services/api/tests/test_chat.py`)

**Test Coverage:**

- ✅ Intent detection (all 8 intents)
- ✅ Intent explanations
- ✅ Chat endpoint health
- ✅ List intents endpoint
- ✅ Empty/invalid messages
- ✅ Basic queries
- ✅ Structured filters
- ✅ Multi-turn conversations
- ✅ Action structure validation
- ✅ Citation structure validation
- ✅ Clean tool exception handling
- ✅ Calendar date extraction

**Run Tests:**

```bash
cd services/api
pytest tests/test_chat.py -v
```

### PowerShell Smoke Test (`scripts/test-chat.ps1`)

**Comprehensive API validation:**

1. Health check
2. List intents
3-10. Test all 8 intent types
11. Query with structured filters
12. Multi-turn conversation

**Run Test:**

```powershell
cd d:/ApplyLens
pwsh ./scripts/test-chat.ps1
```

**Expected Output:**

```
=== Phase 5 Chat Assistant - API Tests ===

1. Health Check
  Status: ok
  Service: chat
  ✅ PASSED

2. List Available Intents
  Found 8 intents:
    • summarize: Summarize matching emails in a concise format
    • find: Find and list specific emails with reasons
    ...
  ✅ PASSED

3. Intent Detection Tests

Testing: Summarize Intent
  Query: "Summarize recent emails about job applications"
  Intent: summarize
  Answer: Found 23 emails. Top matches:...
  Citations: 10 emails
  Actions: 0 proposed
  Results: 23 / 127 searched
  ✅ PASSED

...

=== Test Summary ===
  ✅ Passed:  12
  ❌ Failed:  0
  📊 Total:   12

🎉 All tests passed!
```

### Frontend Testing

**Manual UI Testing:**

1. Navigate to <http://localhost:5175/chat>
2. Click quick-action chips
3. Type custom queries
4. Verify:
   - Intent detection correct
   - Citations displayed
   - Actions count shown
   - Error handling works
   - Loading states appear

---

## Configuration

### Elasticsearch Index

**Required fields in `emails` index:**

- `subject` (text)
- `body_text` (text)
- `sender` (keyword)
- `sender_domain` (keyword)
- `recipient` (keyword)
- `received_at` (date)
- `category` (keyword)
- `labels` (keyword array)
- `risk_score` (integer)
- `body_vector` (dense_vector, optional for semantic search)

### Environment Variables

**Backend:**

- `ELASTICSEARCH_URL` - ES connection string (default: <http://localhost:9200>)
- `CORS_ALLOW_ORIGINS` - Allowed origins (default: <http://localhost:5175>)

**Frontend:**

- `VITE_API_BASE` - API base URL (default: /api, uses proxy)

---

## API Reference

### POST /api/chat

**Description:** Main chat endpoint for conversational queries.

**Request Body:**

```json
{
  "messages": [
    {"role": "user", "content": "string"}
  ],
  "filters": {
    "category": "string",
    "risk_min": 0,
    "risk_max": 100,
    "sender_domain": "string",
    "date_from": "YYYY-MM-DD",
    "date_to": "YYYY-MM-DD",
    "labels": ["string"]
  },
  "max_results": 50
}
```

**Response:**

```json
{
  "intent": "string",
  "intent_explanation": "string",
  "answer": "string",
  "actions": [
    {
      "action": "string",
      "email_id": "string",
      "params": {}
    }
  ],
  "citations": [
    {
      "id": "string",
      "subject": "string",
      "sender": "string",
      "received_at": "string",
      "category": "string",
      "risk_score": 0
    }
  ],
  "search_stats": {
    "total_results": 0,
    "returned_results": 0,
    "query": "string",
    "filters": {}
  }
}
```

### GET /api/chat/intents

**Description:** List all available intents with patterns and descriptions.

**Response:**

```json
{
  "intent_name": {
    "patterns": ["regex1", "regex2"],
    "description": "string"
  }
}
```

### GET /api/chat/health

**Description:** Health check for chat service.

**Response:**

```json
{
  "status": "ok",
  "service": "chat"
}
```

---

## Troubleshooting

### Issue: Chat endpoint returns 500 error

**Possible Causes:**

1. Elasticsearch not running
2. `emails` index doesn't exist
3. Missing required fields in ES documents

**Solution:**

```bash
# Check ES health
curl http://localhost:9200/_cluster/health

# Check emails index
curl http://localhost:9200/emails/_count

# Check API logs
docker compose logs api
```

### Issue: No search results returned

**Possible Causes:**

1. No emails indexed in Elasticsearch
2. Query doesn't match any documents
3. Filters too restrictive

**Solution:**

```bash
# Check email count
curl http://localhost:9200/emails/_search?size=0

# Test search manually
curl -X POST http://localhost:9200/emails/_search \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match_all": {}}, "size": 1}'
```

### Issue: Semantic search not working

**Symptom:** Only keyword results returned, no KNN results.

**Cause:** `body_vector` field not indexed.

**Solution:**

```python
# Embeddings are optional - system works with keyword-only
# To enable semantic search:
# 1. Add body_vector field to ES mapping (dense_vector)
# 2. Replace embed_query() in text.py with real embeddings
# 3. Re-index all emails with vectors
```

### Issue: Intent detection wrong

**Symptom:** User says "find" but gets "summarize" intent.

**Solution:**

- Check intent patterns in `intent.py`
- Add more specific patterns for your use case
- Consider adding LLM-based intent classification

### Issue: Frontend shows "Failed to get response"

**Possible Causes:**

1. API not running
2. CORS issues
3. Network error

**Solution:**

```powershell
# Check API health
curl http://localhost:8003/api/chat/health

# Check browser console for CORS errors
# Verify VITE_API_BASE is correct in .env.local

# Test API directly
Invoke-WebRequest -Uri "http://localhost:8003/api/chat/health"
```

---

## Future Enhancements

### 1. Real Embeddings

Replace fallback with OpenAI or Ollama embeddings:

```python
# app/core/text.py
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def embed_query(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding
```

### 2. LLM-Based Intent Detection

Enhance with GPT-4o-mini for ambiguous cases:

```python
# app/core/intent.py
def detect_intent_llm(text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Classify user intent: summarize, find, clean, ..."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content.strip().lower()
```

### 3. Streaming Responses

Implement Server-Sent Events (SSE) for real-time token generation:

```python
# app/routers/chat.py
@router.post("/stream")
async def chat_stream(req: ChatRequest):
    async def generate():
        # Detect intent
        intent = detect_intent(req.messages[-1].content)
        yield f"data: {json.dumps({'type': 'intent', 'value': intent})}\n\n"
        
        # Stream answer tokens
        for token in generate_answer_tokens(intent, rag):
            yield f"data: {json.dumps({'type': 'token', 'value': token})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### 4. Multi-Modal Search

Add image/attachment search:

```python
# Search for "emails with PDFs"
# Search for "emails with receipts"
# Search for "contracts sent last month"
```

### 5. Conversation Memory

Store conversation history in database for context:

```python
# Track user preferences
# Remember previous queries
# Suggest follow-up questions
```

### 6. Voice Input

Add speech-to-text for hands-free queries:

```typescript
// Frontend: Web Speech API
const recognition = new webkitSpeechRecognition()
recognition.onresult = (event) => {
  const transcript = event.results[0][0].transcript
  sendChatMessage(transcript)
}
```

---

## Summary

✅ **Phase 5 Complete**

**Backend (5 modules):**

- `intent.py` - Rule-based intent detection
- `rag.py` - Hybrid keyword + semantic search
- `text.py` - Embedding utilities (with fallback)
- `mail_tools.py` - 8 specialized mail functions
- `chat.py` - FastAPI router with 3 endpoints

**Frontend (4 components):**

- `chatClient.ts` - Type-safe API client
- `MailChat.tsx` - Conversational UI component
- `ChatPage.tsx` - Page wrapper
- Navigation updates (AppHeader, App.tsx)

**Testing:**

- 40+ pytest tests (intent detection, endpoint validation)
- PowerShell smoke test (12 test cases)

**Documentation:**

- Complete architecture guide
- 8 usage examples
- API reference
- Troubleshooting guide
- Integration notes (Phase 4)

**Next Steps:**

1. Run full stack: `docker compose up -d && npm run dev`
2. Navigate to: <http://localhost:5175/chat>
3. Try quick-action chips
4. Test natural language queries
5. Review citations and proposed actions

🎉 **ApplyLens is now a conversational mailbox assistant!**
