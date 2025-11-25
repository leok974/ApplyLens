# ApplyLens Observability Copilot - Architecture

## System Overview

ApplyLens Observability Copilot extends the ApplyLens job-inbox manager with Gemini-powered AI classification and comprehensive Datadog observability for the Google Cloud AI Partner Catalyst hackathon.

### Architecture Diagram

```mermaid
flowchart LR
  %% Style
  classDef svc fill:#111827,stroke:#4B5563,stroke-width:1,color:#E5E7EB,rx:6,ry:6;
  classDef ext fill:#020617,stroke:#6B7280,stroke-width:1,color:#E5E7EB,rx:6,ry:6,stroke-dasharray:3 3;
  classDef db fill:#030712,stroke:#0EA5E9,stroke-width:1,color:#E5E7EB,rx:6,ry:6;
  classDef obs fill:#020617,stroke:#F97316,stroke-width:1,color:#F97316,rx:6,ry:6;
  classDef llm fill:#020617,stroke:#22C55E,stroke-width:1,color:#BBF7D0,rx:6,ry:6;

  %% Users & Gmail
  U[User<br/>Browser]:::ext
  G[Gmail<br/>User mailbox]:::ext

  %% Web App
  subgraph WEB[ApplyLens Web (React/Vite)]
    W[SPA UI<br/>(/today, inbox, tracker)]:::svc
  end

  %% API & Core Services
  subgraph API[ApplyLens API (FastAPI)]
    direction TB
    A[API Gateway & Router<br/>/agent /emails /search /today]:::svc

    subgraph CORE[Core Services]
      direction TB
      ING[Ingest & Gmail Sync]:::svc
      CLS[Classifier & Extractor<br/>(Gemini path + heuristics)]:::svc
      SRCH[Search Service<br/>(ES queries)]:::svc
      SEC[Security & Risk Analyzer]:::svc
    end
  end

  %% Data Stores
  subgraph DATA[Data Layer]
    direction TB
    PG[(Postgres<br/>apps, metrics, profiles)]:::db
    ES[(Elasticsearch<br/>email index)]:::db
    R[(Redis<br/>cache & limits)]:::db
  end

  %% LLM / Vertex
  subgraph LLM[Google Cloud AI]
    V[Gemini / Vertex AI<br/>LLM endpoints]:::llm
  end

  %% Datadog Observability
  subgraph DD[Datadog]
    direction TB
    DDM[Metrics<br/>llm_latency_ms, llm_error_rate,<br/>ingest_lag_seconds, cost]:::obs
    DDT[Traces<br/>spans: ingest, classify, extract,<br/>search, risk_analyzer]:::obs
    DDL[Logs<br/>structured, PII-redacted]:::obs
    DDB[Dashboards & SLOs<br/>LLM Health, Freshness, Security]:::obs
    DDMON[Monitors & Incidents<br/>latency spike, error burst,<br/>cost anomaly, risk spike]:::obs
  end

  %% Traffic generator
  TG[Traffic Generator CLI<br/>normal/latency/error/token-bloat modes]:::ext

  %% Flows

  %% User ↔ Web ↔ API
  U -->|HTTPS| W
  W -->|REST /agent /today /search| A

  %% Gmail ingest
  G -->|Gmail API<br/>threads/messages| ING
  ING --> PG
  ING --> ES

  %% LLM classify/extract path
  A --> CLS
  CLS -->|LLM request<br/>classify/extract| V
  V -->|labels/entities + timing| CLS

  %% Core services ↔ data
  CLS --> PG
  CLS --> ES
  SRCH --> ES
  SEC --> PG
  A --> R
  A --> PG

  %% Observability hooks
  A -->|metrics/traces/logs| DDM
  A -->|APM spans| DDT
  A -->|structured logs| DDL
  CLS -->|LLM metrics<br/>latency, tokens, errors| DDM
  ING -->|ingest_lag_seconds| DDM
  SRCH -->|search_latency_ms| DDM
  SEC -->|security_high_risk_rate| DDM

  %% Datadog relationships
  DDM --> DDB
  DDT --> DDB
  DDL --> DDB
  DDMON --> DDB
  DDMON -->|create| INC[Datadog Incidents / Cases<br/>with runbooks]:::obs

  %% Traffic generator ↔ API ↔ Datadog
  TG -->|scripted API calls<br/>/agent, /emails, /search| A
  TG -->|causes| DDMON

  %% Judge / demo view
  JD[Judges / Demo Viewer]:::ext -->|view| W
  JD -->|view dashboards| DDB
  JD -->|inspect incidents| INC
```

## Component Details

### 1. Gemini Integration Layer

**Purpose**: Classify emails and extract job entities using Google's Gemini 1.5 Flash model.

**Components**:
- **`app/llm/gemini_client.py`**: Core Gemini client with timeout and fallback logic
- **`app/llm/integration.py`**: Integration wrapper for email processing pipeline
- **`app/routers/hackathon_demo.py`**: Test endpoints for demo

**Key Features**:
- **Strict timeouts**: 5-second timeout per LLM call
- **Automatic fallback**: Falls back to keyword heuristics on error/timeout
- **Privacy-safe**: No raw email bodies logged
- **Confidence scoring**: Returns confidence level (0.0-1.0) with each classification

**Classification Taxonomy**:
```
job_application  → Application confirmations
interview        → Interview invitations
offer            → Job offers
rejection        → Rejections
other            → Non-job emails
```

**Extraction Schema**:
```json
{
  "company": "string | null",
  "role": "string | null",
  "recruiter_name": "string | null",
  "interview_date": "ISO 8601 | null",
  "salary_mentioned": "boolean"
}
```

### 2. Datadog Observability

**Purpose**: Comprehensive monitoring, tracing, and incident management for LLM operations.

**Components**:
- **`app/observability/datadog.py`**: APM instrumentation and metric emission
- **Datadog Agent**: Collects traces, metrics, logs from containers
- **Custom Dashboards**: LLM Health, Ingest Freshness, Security Signals
- **SLOs**: Latency and freshness targets
- **Monitors**: Automated alerting with incident creation

#### Metrics Emitted

| Metric | Type | Description | Tags |
|--------|------|-------------|------|
| `applylens.llm.latency_ms` | Histogram | LLM request duration | `task_type`, `model`, `env` |
| `applylens.llm.error_total` | Counter | Failed LLM calls | `task_type`, `model`, `error_type` |
| `applylens.llm.tokens_used` | Gauge | Estimated tokens per request | `task_type`, `model` |
| `applylens.llm.cost_estimate_usd` | Gauge | Estimated API cost | `task_type`, `model` |
| `applylens.http.requests_total` | Counter | HTTP request count | `endpoint`, `status` |
| `applylens.ingest.lag_seconds` | Histogram | Gmail → searchable lag | `user` |
| `applylens.search.latency_ms` | Histogram | Elasticsearch query time | `index` |

#### APM Traces

**Span Hierarchy**:
```
http.request /hackathon/classify
├─ applylens.llm.classify
│  ├─ vertexai.generate_content
│  └─ gemini.parse_response
└─ applylens.db.query
```

**Span Tags**:
- `task_type`: classify | extract
- `model_provider`: gemini | heuristic
- `env`: dev | hackathon | prod
- `service`: applylens-api-hackathon
- `tokens_estimate`: Integer

#### SLOs Defined

1. **LLM Classify Latency**
   - **Target**: 99% of classify calls < 2000ms over 7 days
   - **Error Budget**: 1% can exceed 2s

2. **Ingest Freshness**
   - **Target**: 99% of threads searchable within 5 minutes over 7 days
   - **Error Budget**: 1% can exceed 5min

#### Monitors Configured

1. **LLM Latency Spike**
   - **Trigger**: p95 `llm_latency_ms` > 3000ms for 5 minutes
   - **Action**: Create incident with dashboard link, trace samples
   - **Runbook**: Check Gemini quota, network latency, prompt complexity

2. **LLM Error Burst**
   - **Trigger**: `llm_error_rate` > 5% for 10 minutes
   - **Action**: Create incident with error codes, fallback stats
   - **Runbook**: Check API keys, quota limits, prompt validity

3. **Token/Cost Anomaly**
   - **Trigger**: `llm_tokens_used` > 3x baseline for 10 minutes
   - **Action**: Create incident with suspected prompt loops
   - **Runbook**: Check for retry storms, prompt bloat, infinite loops

### 3. Traffic Generator

**Purpose**: Generate controlled load to demonstrate monitoring and incident response.

**Location**: `scripts/traffic_generator.py`

**Modes**:
1. **normal_traffic**: Baseline healthy traffic
2. **latency_injection**: Trigger latency monitors (2-5s delays)
3. **error_injection**: Trigger error rate monitors (50% malformed requests)
4. **token_bloat**: Trigger cost monitors (10,000+ char prompts)

**Usage**:
```bash
python scripts/traffic_generator.py \
  --mode latency_injection \
  --rate 20 \
  --duration 120
```

## Data Flow

### Email Classification Flow

```
1. User receives email in Gmail
   │
   ▼
2. ApplyLens fetches via Gmail API
   │
   ▼
3. Email stored in PostgreSQL
   │
   ▼
4. Classification triggered (if USE_GEMINI_FOR_CLASSIFY=1)
   │
   ├─ Datadog span started: applylens.llm.classify
   │
   ├─ Gemini API called with timeout
   │  │
   │  ├─ Success → Parse JSON response
   │  │             └─ Return {intent, confidence, reasoning}
   │  │
   │  └─ Timeout/Error → Fallback to heuristics
   │                     └─ Return {intent, confidence, model_used: "heuristic"}
   │
   ├─ Datadog metrics emitted:
   │  • llm_latency_ms
   │  • llm_tokens_used
   │  • llm_cost_estimate_usd
   │
   └─ Result stored in email metadata
   │
   ▼
5. Email indexed in Elasticsearch with Gemini tags
   │
   ▼
6. User searches/views email with AI classification
```

### Incident Creation Flow

```
1. Traffic generator sends latency_injection requests
   │
   ▼
2. p95 latency climbs above 3000ms
   │
   ▼
3. Datadog monitor evaluates metric (every 1 min)
   │
   ▼
4. Monitor threshold breached for 5 consecutive minutes
   │
   ▼
5. Monitor transitions to ALERT state
   │
   ▼
6. Incident auto-created with:
   • Title: "LLM latency spike detected"
   • Severity: High
   • Fields: What/Impact/Cause/Steps/Fallback
   • Links: Dashboard, trace samples
   │
   ▼
7. Team receives notification (Slack/PagerDuty/email)
   │
   ▼
8. Responder follows runbook in incident
   │
   ▼
9. Issue resolved (traffic generator stopped)
   │
   ▼
10. Monitor returns to OK state
    │
    ▼
11. Incident marked as resolved
```

## Security & Privacy

### PII Protection

1. **No raw email bodies in logs**
   - Only subject + snippet (first 200 chars)
   - User IDs hashed in traces

2. **Gemini prompt safety**
   - Truncate emails to 300 characters
   - Strip attachments before sending
   - No credit card numbers, SSNs sent to LLM

3. **Datadog log redaction**
   - Email addresses → `user@***`
   - Phone numbers → `***-***-1234`
   - Regex-based PII scrubbing

### Access Control

- **Gmail OAuth**: User consent required for email access
- **Datadog RBAC**: Only ops team can view traces
- **API authentication**: Session cookies for user identity

## Deployment

### Hackathon Environment

**Docker Compose Stack**:
```yaml
services:
  datadog-agent    # Metrics/traces/logs collector
  db               # PostgreSQL
  redis            # Cache + rate limiting
  elasticsearch    # Search index
  api              # FastAPI with Gemini + Datadog
  web              # React frontend
```

**Environment Variables** (`.env.hackathon`):
```bash
# Gemini
USE_GEMINI_FOR_CLASSIFY=1
GOOGLE_CLOUD_PROJECT=your-project
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TIMEOUT_SECONDS=5.0

# Datadog
DD_SERVICE=applylens-api-hackathon
DD_ENV=hackathon
DD_API_KEY=your-key
DD_TRACE_ENABLED=true
```

### Startup Sequence

1. Datadog agent starts first (collects from all containers)
2. Database + Redis + Elasticsearch start
3. API starts, initializes Gemini client, patches Datadog
4. Web frontend starts, connects to API

**Health Checks**:
- API: `GET /health/live` → `{"status": "ok"}`
- Gemini: `GET /debug/llm` → Provider status
- Datadog: `docker logs datadog-agent` → Check for errors

## Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| LLM classify latency (p50) | < 500ms | Fast user experience |
| LLM classify latency (p95) | < 2000ms | Acceptable for background |
| LLM classify latency (p99) | < 3000ms | Alert threshold |
| Error rate | < 1% | High reliability |
| Token usage per classify | ~150 tokens | Cost efficiency |
| Cost per 1000 classifies | ~$0.01 | Budget-friendly |

## Monitoring Strategy

### Real-Time Dashboards

1. **LLM Health Dashboard**
   - Latency timeseries (p50/p95/p99)
   - Error rate gauge
   - Token usage rate
   - Cost estimate counter

2. **Ingest Freshness Dashboard**
   - Gmail fetch lag histogram
   - Indexing backlog gauge
   - Email volume timeseries

3. **Security Signals Dashboard**
   - High-risk email rate
   - Quarantine actions
   - Phishing detections

### Alert Fatigue Prevention

- **Alert only on actionable issues**:
  - Latency > 3s sustained (not transient spikes)
  - Error rate > 5% sustained (not single failures)
  - Cost > 3x baseline sustained (not peak hours)

- **Smart incident templates**:
  - Pre-filled likely causes
  - Runbook steps included
  - Dashboard + trace links auto-attached

## Demo Video Script (3 minutes)

**0:00-0:20** - Problem & Solution
- Show overflowing job-search inbox
- Introduce ApplyLens AI assistant
- Highlight Gemini + Datadog integration

**0:20-1:00** - Architecture Walkthrough
- Show diagram with Gemini classification
- Explain fallback to heuristics
- Show Datadog observability layer

**1:00-2:10** - Dashboard Tour
- Open Datadog LLM Health dashboard
- Show latency p95 < 500ms (green)
- Show error rate 0% (green)
- Show SLO at 99.9% compliance

**2:10-2:40** - Trigger Incident
- Run traffic generator: `--mode latency_injection`
- Watch latency spike to 4000ms (red)
- Show monitor fire: "LLM latency spike"
- Navigate to auto-created incident
- Show trace waterfall with slow Gemini span

**2:40-3:00** - Resolution & Wrap
- Stop traffic generator
- Watch latency return to normal
- Resolve incident
- Show final stats: uptime, cost, volume
- Call to action: "Visit our demo at..."

## Future Enhancements (Post-Hackathon)

1. **Multi-model Support**
   - A/B test Gemini vs GPT-4
   - Route based on latency/cost

2. **Advanced Monitoring**
   - Drift detection (classification distribution changes)
   - Feedback loop from user corrections

3. **Cost Optimization**
   - Batch classification for bulk imports
   - Cache frequent classifications

4. **Security Enhancements**
   - Anomaly detection on email content
   - Auto-quarantine high-risk emails

---

**For questions or support**: See `HACKATHON.md` in repo root.
