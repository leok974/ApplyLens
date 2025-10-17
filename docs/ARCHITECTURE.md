# Architecture

This document describes the high-level architecture of ApplyLens, including system components, data flow, and key design decisions.

## System Overview

ApplyLens is a full-stack web application for intelligent job application email management, built with a microservices-inspired architecture using Docker containers.

```text
┌──────────────────────────────────────────────────────────────────┐
│                          Client Browser                          │
│                    (React + Vite @ :5175)                       │
└────────────────────┬─────────────────────────────────────────────┘
                     │ HTTP/WebSocket
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Nginx Reverse Proxy                         │
│              (Routes /api/* → Backend, /* → Frontend)            │
└────────────────────┬─────────────────────────────────────────────┘
                     │
         ┌───────────┴────────────┐
         ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│  FastAPI Backend│      │  Vite Frontend  │
│   (Python 3.11) │      │  (React + TS)   │
│                 │      │                 │
│  • REST API     │      │  • SPA UI       │
│  • Gmail Sync   │      │  • shadcn/ui    │
│  • ML Models    │      │  • TailwindCSS  │
│  • WebSockets   │      └─────────────────┘
└────────┬────────┘
         │
         ├─────────────────┐
         ▼                 ▼
┌──────────────┐   ┌──────────────┐
│  PostgreSQL  │   │Elasticsearch │
│   Database   │   │   (Search)   │
│              │   │              │
│  • Emails    │   │  • Full-text │
│  • Apps      │   │  • Analytics │
│  • Policies  │   │  • Facets    │
│  • Users     │   └──────────────┘
└──────────────┘
         │
         ▼
  ┌──────────────┐
  │  Gmail API   │
  │   (OAuth)    │
  └──────────────┘
```text

## Core Components

### 1. Frontend (`services/web`)

**Technology:** React 18 + TypeScript + Vite

**Key Features:**

- Server-Side Events (SSE) for real-time updates
- shadcn/ui component library
- TailwindCSS for styling
- Zustand for state management
- React Router for navigation

**Main Views:**

- Inbox (email list with filters, search, pagination)
- Email detail panel (thread view, risk scores, actions)
- Application tracker (job applications dashboard)
- Security dashboard (policies, risk thresholds)
- Settings (Gmail OAuth, preferences)

### 2. Backend API (`services/api`)

**Technology:** FastAPI + Python 3.11 + SQLAlchemy

**Key Modules:**

```text
app/
├── main.py                 # FastAPI application entry point
├── settings.py             # Configuration management
├── db/
│   ├── session.py          # Database connection
│   └── models.py           # SQLAlchemy ORM models
├── routers/
│   ├── emails.py           # Email CRUD operations
│   ├── applications.py     # Job application tracking
│   ├── policies.py         # Security policy management
│   ├── labels.py           # ML labeling endpoints
│   └── auth.py             # Gmail OAuth flow
├── services/
│   ├── gmail_service.py    # Gmail API integration
│   ├── es_service.py       # Elasticsearch queries
│   └── risk_service.py     # Confidence learning
└── labeling/
    ├── export_weak_labels.py  # Weak supervision
    ├── train_ml.py            # Model training
    └── label_model.joblib     # Trained model
```text

**API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/emails` | GET | List emails with filters |
| `/emails/{id}` | GET | Get email details |
| `/emails/sync` | POST | Trigger Gmail sync |
| `/applications` | GET | List job applications |
| `/applications/{id}` | PATCH | Update application status |
| `/policies` | GET, POST | Manage security policies |
| `/labels/apply` | POST | Apply ML labels to emails |
| `/auth/google` | GET | Initiate OAuth flow |
| `/health` | GET | Health check |

### 3. Database (PostgreSQL 16)

**Schema Overview:**

```sql
-- Core tables
emails (
  id UUID PRIMARY KEY,
  gmail_message_id TEXT UNIQUE,
  subject TEXT,
  sender TEXT,
  sender_domain TEXT,
  body TEXT,
  received_at TIMESTAMP,
  user_id TEXT,
  category TEXT,  -- application, rejection, interview, offer, other
  risk_score FLOAT,
  is_quarantined BOOLEAN,
  CONSTRAINT check_risk_score CHECK (risk_score BETWEEN 0 AND 100)
)

applications (
  id UUID PRIMARY KEY,
  email_id UUID REFERENCES emails(id),
  company TEXT,
  position TEXT,
  applied_date DATE,
  status TEXT,  -- applied, interview, offer, rejected
  notes TEXT,
  user_id TEXT
)

policies (
  id UUID PRIMARY KEY,
  name TEXT,
  condition_type TEXT,  -- sender_domain, keyword, risk_score
  condition_value TEXT,
  action TEXT,  -- label, quarantine, archive, delete
  enabled BOOLEAN,
  user_id TEXT
)

user_weights (
  id UUID PRIMARY KEY,
  user_id TEXT,
  feature TEXT,  -- sender_domain:xyz.com, keyword:urgent
  weight FLOAT,  -- positive = safe, negative = risky
  updated_at TIMESTAMP
)
```text

**Migrations:** Managed by Alembic (`services/api/alembic/`)

### 4. Search Engine (Elasticsearch 8.x)

**Index:** `emails_v1-000001`

**Mapping:**

```json
{
  "mappings": {
    "properties": {
      "gmail_message_id": { "type": "keyword" },
      "subject": { "type": "text", "analyzer": "standard" },
      "sender": { "type": "keyword" },
      "sender_domain": { "type": "keyword" },
      "body": { "type": "text", "analyzer": "standard" },
      "received_at": { "type": "date" },
      "category": { "type": "keyword" },
      "risk_score": { "type": "float" },
      "user_id": { "type": "keyword" }
    }
  }
}
```text

**Use Cases:**

- Full-text search across subject and body
- Faceted filters (category, sender_domain, date range)
- Aggregations for analytics
- Risk score distribution

## Data Flow

### Email Sync Flow

```text
1. User clicks "Sync" → POST /emails/sync
2. Backend fetches messages via Gmail API
3. For each message:
   a. Extract metadata (sender, subject, date)
   b. Calculate risk score using confidence learning
   c. Apply ML categorization model
   d. Check security policies
   e. Save to PostgreSQL
   f. Index in Elasticsearch
4. Return sync summary to frontend
```text

### Search Flow

```text
1. User enters search query → GET /emails?q=...&category=...
2. Backend builds Elasticsearch query
3. ES returns matching document IDs + facets
4. Backend fetches full records from PostgreSQL
5. Return enriched results to frontend
```text

### Risk Scoring Flow

```text
1. New email arrives
2. Extract features:
   - sender_domain
   - keywords in subject/body
   - time-of-day, day-of-week
   - link count, attachment presence
3. Load user_weights from database
4. Calculate weighted sum:
   risk_score = Σ (feature_weight × feature_presence)
5. Normalize to 0-100 range
6. If risk_score > threshold → quarantine
```text

### Policy Execution Flow

```text
1. Email saved to database
2. Fetch all enabled policies for user
3. For each policy:
   a. Evaluate condition (e.g., sender_domain == "spam.com")
   b. If match → apply action (label, quarantine, archive)
4. Update email record
5. Sync changes to Elasticsearch
```text

## Security & Authentication

### Gmail OAuth 2.0

```text
1. User clicks "Connect Gmail"
2. Redirect to Google OAuth consent screen
3. User grants permissions (read Gmail, send on behalf)
4. Google redirects to callback URL with auth code
5. Backend exchanges code for access + refresh tokens
6. Store encrypted tokens in database
7. Use refresh token to maintain access
```text

### API Security

- **CORS:** Configured via `CORS_ORIGINS` environment variable
- **Rate Limiting:** (TODO) Implement per-user rate limits
- **Input Validation:** Pydantic models validate all request bodies
- **SQL Injection:** SQLAlchemy ORM prevents injection
- **XSS:** React escapes user input by default

---

## Agentic System Architecture (Phase 3)

### Overview

The agentic system enables autonomous workflows with built-in safety controls, resource limits, and comprehensive auditing.

```text
┌──────────────────────────────────────────────────────────────────┐
│                     Agent Execution Flow                          │
└──────────────────────────────────────────────────────────────────┘

    POST /agents/execute
           │
           ▼
    ┌─────────────┐
    │   Router    │  Validate request, check budgets
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  Executor   │  Inject providers, enforce limits
    └──────┬──────┘
           │
           ├──────────────┬──────────────┬──────────────┐
           ▼              ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  Agent   │   │Approvals │  │ Budgets  │  │Artifacts │
    │          │   │          │  │          │  │          │
    │ • Plan   │   │ • Policy │  │ • Time   │  │ • JSON   │
    │ • Execute│   │ • Gates  │  │ • Ops    │  │ • MD     │
    └────┬─────┘   └────┬─────┘  └────┬─────┘  └────┬─────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
    ┌──────────────────────────────────────────────────────┐
    │              Providers (ES, BQ, Gmail)               │
    └──────────────────────────────────────────────────────┘
           │
           ▼
    ┌─────────────┐
    │   Auditor   │  Log to database
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  EventBus   │  Broadcast SSE events
    └─────────────┘
```

### Core Components

#### 1. Agent Registry

**File:** `app/agents/registry.py`

```python
AGENT_REGISTRY = {
    "warehouse_health": WarehouseHealthAgent,
    "inbox_triage": InboxTriageAgent,          # Phase 3
    "knowledge_update": KnowledgeUpdaterAgent, # Phase 3
    "insights_writer": InsightsWriterAgent     # Phase 3
}
```

#### 2. Executor (`app/agents/executor.py`)

**Responsibilities:**
- Inject dependencies (providers, auditor, event_bus)
- Enforce budgets (time, operations)
- Gate actions with `allow_actions` flag
- Track operation counts
- Handle errors and timeouts

**Budget Enforcement:**
```python
# Before execution
if budget_ms or budget_ops:
    start_time = time.time()
    ops_count = 0

# During execution
ops_count += 1  # Track each provider call

# After execution
elapsed_ms = (time.time() - start_time) * 1000
budget_status = Approvals.check_budget(
    elapsed_ms, ops_count, budget_ms, budget_ops
)
if budget_status["exceeded"]:
    log.warning("Budget exceeded")
```

#### 3. Approvals System (`app/utils/approvals.py`)

**Policy Checks:**

```python
class Approvals:
    @staticmethod
    def allow(agent_name, action, context) -> bool:
        """Check if action is allowed by policy."""
        
        # Always allow read-only
        if action in ['query', 'fetch', 'read', 'get', 'list', 'search']:
            return True
        
        # Always deny high-risk
        if action in ['quarantine', 'delete', 'purge', 'drop']:
            return False  # Phase 3: denied, Phase 4: require approval
        
        # Check size limits
        if context.get('size', 0) > 1000:
            return False
        
        # Check budget limits
        if context.get('budget_exceeded', False):
            return False
        
        # Check risk thresholds
        if context.get('risk_score', 0) > 95:
            return False
        
        # Default: allow moderate-risk actions
        return True
    
    @staticmethod
    def check_budget(elapsed_ms, ops_count, budget_ms, budget_ops):
        """Validate time and operation budgets."""
        time_exceeded = budget_ms and elapsed_ms > budget_ms
        ops_exceeded = budget_ops and ops_count > budget_ops
        
        return {
            "exceeded": time_exceeded or ops_exceeded,
            "time_limit": budget_ms,
            "time_used": elapsed_ms,
            "ops_limit": budget_ops,
            "ops_used": ops_count
        }
```

**Approval Flow (Phase 4):**
```text
Agent → Request approval → Approvals Tray → Human review → Approved/Denied
```

#### 4. Artifacts Store (`app/utils/artifacts.py`)

**Purpose:** Persist agent outputs for review and auditing

**File Structure:**
```text
agent/artifacts/
├── inbox_triage/
│   ├── report_2025-10-17_103045.md
│   └── results_2025-10-17_103045.json
├── knowledge_update/
│   ├── synonyms.diff.json
│   └── synonyms.diff.md
└── insights_writer/
    ├── email_activity_2025-W42.md
    └── email_activity_2025-W42.json
```

**API:**
```python
from app.utils.artifacts import artifacts_store

# Write markdown
artifacts_store.write(
    path='report.md',
    content=report_text,
    agent_name='inbox_triage'
)

# Write JSON
artifacts_store.write_json(
    path='results.json',
    data={'total': 100},
    agent_name='inbox_triage'
)

# Read artifact
content = artifacts_store.read(
    path='report.md',
    agent_name='inbox_triage'
)

# List artifacts
files = artifacts_store.list_files(
    agent_name='inbox_triage',
    pattern='*.json'
)

# Timestamped paths
path = artifacts_store.get_timestamped_path(
    prefix='report',
    extension='md',
    agent_name='inbox_triage'
)  # → "report_2025-10-17_103045.md"

# Weekly paths (ISO 8601)
path = artifacts_store.get_weekly_path(
    prefix='insights',
    extension='md'
)  # → "insights_2025-W42.md"
```

### Phase 3 Agents

#### Inbox Triage Agent

**Purpose:** Automatically triage incoming emails by risk level

**Architecture:**
```text
Gmail API → Fetch emails → RiskScorer → Classify → Label/Quarantine → Artifacts
```

**RiskScorer:**
- Suspicious keywords (15 points each, max 40)
- Suspicious TLDs (20 points)
- Phishing patterns (20 points)
- Gmail spam labels (50 points)
- Safe domain allowlist (score = 0)

**Output:** Markdown report + JSON results

#### Knowledge Updater Agent

**Purpose:** Sync Elasticsearch configuration from BigQuery data marts

**Architecture:**
```text
BigQuery → Query mart → Fetch ES config → Generate diff → Apply (with approval) → Artifacts
```

**Diff Types:**
- Added: New items not in current config
- Removed: Items in current but not in new
- Unchanged: Items in both

**Output:** JSON diff + markdown report

#### Insights Writer Agent

**Purpose:** Generate weekly insights reports from warehouse metrics

**Architecture:**
```text
BigQuery → Query current week → Query previous week → Calculate trends → Generate report → Artifacts
```

**Trend Calculation:**
```python
change_pct = ((current - previous) / previous) * 100
direction = '📈' if change_pct > 0 else '📉' if change_pct < 0 else '➡️'
```

**Output:** Markdown report with tables + JSON data

### Safety Model

**Defense in Depth:**

1. **Dry-run by default** - All agents default to dry-run mode
2. **Action gates** - `allow_actions=True` required for mutations
3. **Approval policies** - High-risk actions require human approval (Phase 4)
4. **Budget limits** - Time and operation limits prevent runaway execution
5. **Audit logging** - All runs logged to database
6. **Artifacts** - Outputs persisted for review

**Budget Example:**
```json
{
  "agent_type": "inbox_triage",
  "budget_ms": 30000,    // Max 30 seconds
  "budget_ops": 100,     // Max 100 operations
  "allow_actions": true  // Enable mutations
}
```

If budgets are exceeded:
- Warning logged (execution completes)
- Future: abort execution or throttle
- Phase 4: require approval for continuation

---

## Monitoring & Observability

### Prometheus Metrics

```python
# services/api/app/metrics.py
email_sync_duration = Histogram("email_sync_duration_seconds")
risk_score_distribution = Histogram("risk_score", buckets=[0, 20, 40, 60, 80, 100])
api_request_duration = Histogram("http_request_duration_seconds")
```text

### Grafana Dashboards

- **Email Overview:** Sync rate, category distribution
- **Risk Analysis:** Risk score histogram, quarantine rate
- **API Performance:** Request latency, error rate
- **System Health:** CPU, memory, database connections

## Scalability Considerations

### Current Limitations

- **Single-instance FastAPI:** No horizontal scaling yet
- **PostgreSQL:** Single primary, no replicas
- **Elasticsearch:** Single node

### Future Improvements

1. **Load Balancing:** Nginx → multiple FastAPI instances
2. **Database:** Read replicas for queries, primary for writes
3. **Caching:** Redis for frequently accessed data
4. **Task Queue:** Celery for background jobs (Gmail sync, ML training)
5. **Elasticsearch Cluster:** Multi-node for high availability

## Technology Decisions

### Why FastAPI?

- Async support for I/O-bound tasks (Gmail API, ES queries)
- Automatic OpenAPI documentation
- Pydantic for data validation
- High performance (comparable to Node.js)

### Why Elasticsearch?

- Full-text search with relevance scoring
- Faceted search for filtering
- Real-time indexing
- Aggregations for analytics

### Why PostgreSQL?

- ACID transactions for data integrity
- JSON support for flexible schemas
- Mature ecosystem (SQLAlchemy, Alembic)
- Strong consistency guarantees

### Why React + Vite?

- Fast development with HMR
- Rich ecosystem (shadcn/ui, TailwindCSS)
- TypeScript for type safety
- Vite for fast builds

## See Also

- [Backend Implementation](./BACKEND.md)
- [Frontend Components](./FRONTEND.md)
- [Security Architecture](./SECURITY.md)
- [Deployment Guide](./OPS.md)
