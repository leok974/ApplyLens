# Architecture

This document describes the high-level architecture of ApplyLens, including system components, data flow, and key design decisions.

## System Overview

ApplyLens is a full-stack web application for intelligent job application email management, built with a microservices-inspired architecture using Docker containers.

```
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
```

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

```
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
```

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
```

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
```

**Use Cases:**

- Full-text search across subject and body
- Faceted filters (category, sender_domain, date range)
- Aggregations for analytics
- Risk score distribution

## Data Flow

### Email Sync Flow

```
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
```

### Search Flow

```
1. User enters search query → GET /emails?q=...&category=...
2. Backend builds Elasticsearch query
3. ES returns matching document IDs + facets
4. Backend fetches full records from PostgreSQL
5. Return enriched results to frontend
```

### Risk Scoring Flow

```
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
```

### Policy Execution Flow

```
1. Email saved to database
2. Fetch all enabled policies for user
3. For each policy:
   a. Evaluate condition (e.g., sender_domain == "spam.com")
   b. If match → apply action (label, quarantine, archive)
4. Update email record
5. Sync changes to Elasticsearch
```

## Security & Authentication

### Gmail OAuth 2.0

```
1. User clicks "Connect Gmail"
2. Redirect to Google OAuth consent screen
3. User grants permissions (read Gmail, send on behalf)
4. Google redirects to callback URL with auth code
5. Backend exchanges code for access + refresh tokens
6. Store encrypted tokens in database
7. Use refresh token to maintain access
```

### API Security

- **CORS:** Configured via `CORS_ORIGINS` environment variable
- **Rate Limiting:** (TODO) Implement per-user rate limits
- **Input Validation:** Pydantic models validate all request bodies
- **SQL Injection:** SQLAlchemy ORM prevents injection
- **XSS:** React escapes user input by default

## Monitoring & Observability

### Prometheus Metrics

```python
# services/api/app/metrics.py
email_sync_duration = Histogram("email_sync_duration_seconds")
risk_score_distribution = Histogram("risk_score", buckets=[0, 20, 40, 60, 80, 100])
api_request_duration = Histogram("http_request_duration_seconds")
```

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
