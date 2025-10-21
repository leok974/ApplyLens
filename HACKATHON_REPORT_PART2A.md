# ApplyLens Architecture & Hackathon Readiness Report (Part 2A)

**Continued from HACKATHON_REPORT_PART1.md**

---

## 5) HTTP API Surface (Backend)

### API Overview

**Base URL:** `https://applylens.app/api` (production) | `http://localhost:8003` (local)  
**Framework:** FastAPI 0.115  
**Auth:** OAuth 2.0 (Google), Session cookies  
**CORS:** `https://applylens.app`, `https://www.applylens.app`

### Authentication & OAuth

**Endpoints:**
```
GET  /auth/google/login              - Start OAuth flow (redirect to Google)
GET  /auth/google/callback           - OAuth callback handler
GET  /oauth/init                     - Initialize OAuth session
GET  /oauth/callback                 - Process OAuth redirect
GET  /oauth/status                   - Check connection status
DELETE /oauth/disconnect             - Revoke access
```

**Flow:**
1. User clicks "Connect Gmail" → `GET /auth/google/login`
2. Redirect to Google consent screen (scopes: `gmail.readonly`, `userinfo.email`)
3. Google redirects back → `GET /auth/google/callback?code=xyz`
4. Exchange code for tokens, store in `oauth_state` table
5. Set session cookie, redirect to `/web/`

**Auth Notes:**
- Tokens encrypted at rest (PostgreSQL)
- Refresh tokens used for long-lived sessions
- State parameter prevents CSRF attacks
- Read-only Gmail access (no send/delete permissions)

### Gmail Integration

**Endpoints:**
```
GET  /gmail/status                   - Connection status (connected/disconnected)
GET  /gmail/inbox                    - Paginated inbox (limit, offset, label_filter)
POST /gmail/backfill                 - Sync N days of history (default: 60)
```

**Example Requests:**
```http
GET /gmail/status
Response: {
  "connected": true,
  "user_email": "user@gmail.com",
  "last_sync": "2025-10-18T10:30:00Z",
  "scopes": ["gmail.readonly", "userinfo.email"]
}

POST /gmail/backfill?days=60&user_email=user@gmail.com
Response: {
  "status": "ok",
  "synced": 2341,
  "skipped": 12,
  "errors": 0,
  "duration_sec": 145.2
}

GET /gmail/inbox?limit=50&offset=0&label_filter=interview
Response: {
  "emails": [...],
  "total": 234,
  "limit": 50,
  "offset": 0
}
```

### Search & Autocomplete

**Endpoints:**
```
GET  /search                         - Full-text search (Elasticsearch)
GET  /search/explain/{doc_id}        - Explain relevance scoring
GET  /suggest                        - Autocomplete suggestions
POST /search/actions/archive         - Batch archive
POST /search/actions/mark_safe       - Mark as safe
POST /search/actions/mark_suspicious - Flag as suspicious
```

**Search Parameters:**
- `q`: Query string (BM25 + synonyms)
- `label_filter`: Array of labels (AND logic)
- `category`: Filter by category
- `risk_min`, `risk_max`: Risk score range
- `from_date`, `to_date`: Date range
- `sender_domain`: Filter by domain
- `sort`: `relevance`, `date`, `risk` (default: relevance)
- `limit`, `offset`: Pagination

**Example:**
```http
GET /search?q=interview&label_filter=interview&sort=date&limit=20
Response: {
  "hits": [
    {
      "id": 123,
      "subject": "Interview Schedule - Software Engineer",
      "sender": "recruiter@example.com",
      "snippet": "...we'd like to schedule your <em>interview</em>...",
      "score": 14.2,
      "labels": ["interview"],
      "risk_score": 5,
      "received_at": "2025-10-15T14:30:00Z"
    }
  ],
  "total": 45,
  "took_ms": 23
}

GET /suggest?q=interv&limit=5
Response: {
  "suggestions": [
    {"text": "interview", "score": 8.5},
    {"text": "interview schedule", "score": 6.2},
    {"text": "phone interview", "score": 5.8}
  ]
}
```

### Email Labeling & Classification

**Endpoints:**
```
POST /labels/apply                   - Label all emails (ML classification)
POST /labels/apply-batch             - Label filtered subset
GET  /labels/stats                   - Category distribution
POST /label/rebuild                  - Rebuild classification model
GET  /label/preview                  - Preview labels before applying
POST /label/email/{email_id}         - Label single email
GET  /labeling/stats                 - Labeling statistics
```

**Categories:**
- `newsletter`: Newsletters, promotional content from known senders
- `promo`: Sales emails, marketing campaigns
- `recruiting`: Job-related emails (ATS platforms, recruiters)
- `bill`: Invoices, receipts, payment notifications

**Example:**
```http
POST /labels/apply
Response: {
  "status": "ok",
  "labeled": 1245,
  "duration_ms": 3421,
  "by_category": {
    "newsletter": 520,
    "promo": 380,
    "recruiting": 245,
    "bill": 100
  }
}

GET /labels/stats
Response: {
  "total": 5000,
  "by_category": {
    "newsletter": 2100,
    "promo": 1500,
    "recruiting": 800,
    "bill": 600
  },
  "unlabeled": 0
}
```

### Application Tracking

**Endpoints:**
```
GET  /applications                   - List applications (paginated, sortable)
POST /applications                   - Create application
GET  /applications/{app_id}          - Get application details
PATCH /applications/{app_id}         - Update application
DELETE /applications/{app_id}        - Delete application
POST /applications/from-email/{id}   - Extract from email
POST /extract                        - Extract job details from text
POST /backfill-from-email            - Batch extract from emails
```

**Multi-Backend Support:**
```http
GET /applications?backend=es&sort=updated_at&order=desc&limit=20
# Backend options: "es" (Elasticsearch) or "bigquery" (warehouse)

GET /applications?backend=bigquery&status=interview&sort=company
# When USE_WAREHOUSE_METRICS=1, queries BigQuery marts
```

**Application Schema:**
```json
{
  "id": "app_123",
  "company": "Acme Corp",
  "role": "Senior Engineer",
  "status": "interview",
  "applied_at": "2025-10-01T00:00:00Z",
  "updated_at": "2025-10-15T10:30:00Z",
  "source": "email",
  "email_id": 456,
  "notes": "Phone screen went well"
}
```

**Statuses:**
- `applied`: Application submitted
- `interview`: Interview scheduled/completed
- `offer`: Offer received
- `rejected`: Application declined
- `accepted`: Offer accepted
- `withdrawn`: Application withdrawn

### Security & Risk Management

**Endpoints:**
```
POST /security/rescan/{email_id}     - Re-analyze email risk
GET  /security/stats                 - Security statistics
POST /security/bulk/rescan           - Batch re-scan
POST /security/bulk/quarantine       - Batch quarantine
POST /security/bulk/release          - Batch release from quarantine
GET  /security/events                - Security event log
GET  /policy/security                - Get security policies
PUT  /policy/security                - Update security policies
```

**Risk Signals:**
- `DMARC_FAIL`, `SPF_FAIL`, `DKIM_FAIL`: Authentication failures
- `URL_MISMATCH`: Display text != actual URL
- `SUSPICIOUS_TLD`: Risky TLDs (.tk, .ml, .ga)
- `NEW_DOMAIN`: Domain < 30 days old
- `BLOCKLISTED`: Known phishing/spam domain
- `URGENT_LANGUAGE`: Pressure tactics
- `SUSPICIOUS_ATTACHMENT`: Risky file types

**Example:**
```http
POST /security/rescan/email_123
Response: {
  "status": "ok",
  "email_id": "email_123",
  "risk_score": 75,
  "quarantined": true,
  "flags": [
    {
      "signal": "DMARC_FAIL",
      "severity": "high",
      "points": 15,
      "details": "DMARC policy: reject"
    },
    {
      "signal": "URL_MISMATCH",
      "severity": "high",
      "points": 20,
      "details": "Display: paypal.com, Actual: paypa1-secure.tk"
    }
  ]
}

GET /security/stats
Response: {
  "quarantined": 23,
  "average_risk": 18.5,
  "high_risk_count": 45,
  "by_signal": {
    "DMARC_FAIL": 12,
    "URL_MISMATCH": 8,
    "SUSPICIOUS_TLD": 15
  }
}
```

### Profile & Analytics

**Endpoints:**
```
GET  /profile/summary                - User profile summary
GET  /profile/senders                - Top senders list
GET  /profile/categories/{category}  - Category details
GET  /profile/time-series            - Email volume trends
POST /profile/rebuild                - Rebuild profile cache
GET  /profile/db-summary             - PostgreSQL-backed summary
GET  /profile/db-interests           - Interest analysis
GET  /profile/db-senders             - Sender breakdown
GET  /profile/db-categories          - Category breakdown
```

**Example:**
```http
GET /profile/summary
Response: {
  "total_emails": 5000,
  "by_category": {
    "newsletter": 2100,
    "promo": 1500,
    "recruiting": 800,
    "bill": 600
  },
  "top_senders": [
    {"sender": "careers@example.com", "count": 45},
    {"sender": "noreply@linkedin.com", "count": 38}
  ],
  "time_range": {
    "oldest": "2025-08-20",
    "newest": "2025-10-18"
  }
}

GET /profile/time-series?days=30&granularity=day
Response: {
  "series": [
    {"date": "2025-10-01", "count": 42, "by_category": {"newsletter": 20, "recruiting": 12}},
    {"date": "2025-10-02", "count": 38, "by_category": {"newsletter": 18, "recruiting": 10}}
  ]
}
```

### Conversational Chat (RAG)

**Endpoints:**
```
POST /chat                           - Chat with inbox (RAG search)
GET  /chat/intents                   - List supported intents
GET  /chat/health                    - Chat service health
GET  /chat/stream                    - SSE stream (experimental)
```

**Supported Intents:**
- `find_emails`: Search for specific emails
- `summarize`: Generate email summaries
- `unsubscribe`: Unsubscribe from newsletters
- `clean_promotions`: Archive/delete promos
- `create_tasks`: Create tasks from emails
- `create_calendar_events`: Schedule from emails
- `follow_up`: Set follow-up reminders
- `flag_suspicious`: Mark emails as suspicious

**Example:**
```http
POST /chat
Body: {
  "messages": [
    {"role": "user", "content": "show me interviews this week"}
  ],
  "filters": {"label_filter": ["interview"]},
  "max_results": 50
}

Response: {
  "answer": "You have 3 interviews scheduled this week:\n\n1. **Microsoft** - Monday 2pm (Phone Screen)\n2. **Google** - Wednesday 10am (Onsite)\n3. **Meta** - Friday 3pm (Team Match)",
  "citations": [
    {
      "email_id": 123,
      "subject": "Microsoft Interview - Software Engineer",
      "sender": "recruiter@microsoft.com",
      "snippet": "...phone screen scheduled for Monday at 2pm..."
    }
  ],
  "actions": [],
  "intent": "find_emails",
  "timing": {
    "es_ms": 45,
    "llm_ms": 0,
    "client_ms": 12
  }
}
```

### Agent System

**Endpoints:**
```
GET  /agents                         - List available agents
POST /agents/{name}/run              - Execute agent
GET  /agents/{name}/runs             - Get agent run history
GET  /agents/events                  - SSE event stream for real-time updates
POST /agents/feedback                - Submit feedback on agent output
GET  /agents/metrics/{agent}         - Agent performance metrics
GET  /agents/health                  - All agents health status
POST /agents/redteam/run             - Run adversarial tests
```

**Available Agents:**
- `inbox_triage`: Classify and quarantine risky emails
- `knowledge_update`: Update knowledge base from emails
- `insights_writer`: Generate weekly insights reports
- `warehouse`: Query BigQuery data warehouse

**Example:**
```http
POST /agents/inbox_triage/run
Body: {
  "objective": "quarantine emails with risk_score >= 70",
  "dry_run": true,
  "params": {
    "tools": ["quarantine", "flag"],
    "date_range": "last_7_days"
  }
}

Response: {
  "status": "ok",
  "run_id": "run_abc123",
  "agent": "inbox_triage",
  "dry_run": true,
  "result": {
    "quarantined": 5,
    "flagged": 12,
    "total_scanned": 234
  },
  "budget_used": {
    "ms": 1234,
    "ops": 5,
    "cost_cents": 0
  }
}

GET /agents/inbox_triage/runs?limit=10
Response: {
  "runs": [
    {
      "run_id": "run_abc123",
      "status": "completed",
      "started_at": "2025-10-18T10:30:00Z",
      "completed_at": "2025-10-18T10:31:15Z",
      "result": {...}
    }
  ]
}
```

### Policy Management (Phase 5.5)

**Endpoints:**
```
GET    /policy/bundles              - List policy bundles
POST   /policy/bundles              - Create new bundle
GET    /policy/bundles/{id}         - Get bundle details
PUT    /policy/bundles/{id}         - Update bundle
DELETE /policy/bundles/{id}         - Delete bundle
GET    /policy/bundles/active       - Get active bundle
POST   /policy/bundles/{id}/activate - Activate bundle (canary)
POST   /policy/bundles/{id}/promote  - Promote canary to production
POST   /policy/bundles/{id}/rollback - Rollback to previous version
POST   /policy/lint                 - Validate policy syntax
POST   /policy/simulate             - What-if simulation
GET    /policy/{id}/export          - Export bundle (JSON)
POST   /policy/import               - Import bundle
```

**Policy Bundle Schema:**
```json
{
  "id": 1,
  "version": "1.2.3",
  "description": "Allow inbox_triage with risk thresholds",
  "rules": [
    {
      "id": "allow-triage-low-risk",
      "agent": "inbox_triage",
      "action": "quarantine",
      "conditions": {"risk_score": 70},
      "effect": "allow",
      "priority": 50,
      "reason": "Auto-quarantine high-risk emails"
    }
  ],
  "state": "active",
  "signature": "sha256:abc123...",
  "created_at": "2025-10-18T10:00:00Z",
  "activated_at": "2025-10-18T11:00:00Z"
}
```

### Approval Workflows

**Endpoints:**
```
POST /approvals                      - Create approval request
GET  /approvals                      - List pending approvals
GET  /approvals/{id}                 - Get approval details
POST /approvals/{id}/decide          - Approve/reject
POST /approvals/{id}/verify          - Verify HMAC signature
POST /approvals/{id}/execute         - Execute approved action
```

**Example:**
```http
POST /approvals
Body: {
  "agent": "knowledge_update",
  "action": "apply_changes",
  "params": {"changes_count": 150},
  "metadata": {"source": "weekly_sync"}
}

Response: {
  "request_id": "req_xyz789",
  "status": "pending",
  "agent": "knowledge_update",
  "action": "apply_changes",
  "signature": "hmac-sha256:...",
  "created_at": "2025-10-18T10:30:00Z",
  "expires_at": "2025-10-25T10:30:00Z"
}

POST /approvals/req_xyz789/decide
Body: {
  "decision": "approved",
  "reviewer": "admin@applylens.com",
  "notes": "Reviewed changes, looks good"
}

Response: {
  "status": "approved",
  "approved_at": "2025-10-18T10:35:00Z"
}
```

### Observability & Monitoring

**Endpoints:**
```
GET  /metrics                        - Prometheus metrics (text format)
GET  /healthz                        - Health check
GET  /live                           - Liveness probe
GET  /debug/500                      - Test error alerting (dev only)
GET  /slo/agents                     - List agent SLOs
GET  /slo/{agent_name}               - Get SLO status
GET  /alerts                         - Active alerts
POST /alerts/{key}/acknowledge       - Acknowledge alert
POST /alerts/{key}/resolve           - Resolve alert
```

**Metrics Exposed:**
- `applylens_http_requests_total` - Request counter by path, method, status
- `applylens_http_request_duration_seconds` - Request latency histogram
- `applylens_agent_runs_total` - Agent execution counter
- `applylens_agent_duration_seconds` - Agent execution time
- `applylens_gmail_sync_emails_total` - Email sync counter
- `applylens_es_index_operations_total` - ES indexing operations

**Example:**
```http
GET /healthz
Response: {"status": "ok"}

GET /metrics
Response: (Prometheus text format)
# TYPE applylens_http_requests_total counter
applylens_http_requests_total{method="GET",path="/search",status="200"} 1234
applylens_http_requests_total{method="POST",path="/chat",status="200"} 567
...
```

### SSE (Server-Sent Events)

**Endpoint:**
```
GET /sse/events                      - Real-time event stream
```

**Event Types:**
- `agent.started`: Agent execution began
- `agent.progress`: Progress update during execution
- `agent.completed`: Agent finished successfully
- `agent.failed`: Agent execution failed
- `policy.activated`: Policy bundle activated
- `sync.started`: Gmail sync started
- `sync.completed`: Gmail sync completed

**Example:**
```http
GET /sse/events

Response: (text/event-stream)
data: {"type": "agent.started", "run_id": "run_123", "agent": "inbox_triage"}

data: {"type": "agent.progress", "run_id": "run_123", "progress": 50, "status": "scanning emails"}

data: {"type": "agent.completed", "run_id": "run_123", "result": {"quarantined": 5}}
```

---

**Continued in HACKATHON_REPORT_PART2B.md**
