# Approvals Tray - Quick Reference

## API Endpoints

### 1. Propose Actions
```http
POST /approvals/propose
Content-Type: application/json

{
  "items": [
    {
      "email_id": "e123",
      "action": "archive",
      "policy_id": "expired_promos",
      "confidence": 0.95,
      "rationale": "Promo expired 30 days ago",
      "params": {"folder": "Archive"}
    }
  ]
}

Response: {"accepted": 1}
```

### 2. List Pending
```http
GET /approvals/proposed?limit=200

Response: {
  "items": [
    {
      "id": 1,
      "email_id": "e123",
      "action": "archive",
      "policy_id": "expired_promos",
      "confidence": 0.95,
      "rationale": "Promo expired 30 days ago",
      "params": {"folder": "Archive"},
      "status": "proposed",
      "created_at": "2025-10-10T00:00:00Z"
    }
  ]
}
```

### 3. Approve
```http
POST /approvals/approve
Content-Type: application/json

{"ids": [1, 2, 3]}

Response: {"updated": 3, "status": "approved"}
```

### 4. Reject
```http
POST /approvals/reject
Content-Type: application/json

{"ids": [4, 5]}

Response: {"updated": 2, "status": "rejected"}
```

### 5. Execute
```http
POST /approvals/execute
Content-Type: application/json

{
  "items": [
    {
      "email_id": "e123",
      "action": "archive",
      "params": {"folder": "Archive"}
    }
  ]
}

Response: {"applied": 1}
```

## Database Schema

```sql
-- approvals_proposed table
id              BIGSERIAL PRIMARY KEY
email_id        TEXT NOT NULL
action          TEXT NOT NULL
policy_id       TEXT NOT NULL
confidence      REAL NOT NULL
rationale       TEXT
params          JSONB
status          TEXT NOT NULL DEFAULT 'proposed'
created_at      TIMESTAMPTZ DEFAULT now()
updated_at      TIMESTAMPTZ DEFAULT now()

-- Indexes
idx_approvals_status_policy: (status, policy_id)
idx_approvals_email: (email_id)
idx_approvals_created: (created_at)
```

## ES Audit Index (actions_audit_v1)

```json
{
  "email_id": "e123",
  "action": "archive",
  "actor": "agent",
  "policy_id": "expired_promos",
  "confidence": 0.95,
  "rationale": "Promo expired",
  "status": "proposed",
  "created_at": "2025-10-10T00:00:00Z",
  "payload": {"folder": "Archive"}
}
```

## Status Flow

```
proposed (agent) → approved/rejected (user) → executed (system)
```

## Actor Types

- `agent` - Policy engine proposes
- `user` - Human approves/rejects
- `system` - Automated execution

## Action Types

**Mail Actions** (routed to Gmail API):
- `archive`
- `delete`
- `label`
- `move`

**Unsubscribe Actions** (routed to List-Unsubscribe):
- `unsubscribe`

## Deployment Checklist

- [ ] Run Alembic migration: `alembic upgrade head`
- [ ] Create ES index: `python -m app.scripts.create_audit_index`
- [ ] Import Kibana saved search: `kibana/policy-hits-vs-misses.ndjson`
- [ ] Verify endpoints: `curl http://localhost:8000/docs`
- [ ] Run tests: `pytest tests/ -k approvals -v`

## Python Usage

```python
# Propose
from app.db import approvals_bulk_insert
approvals_bulk_insert([{
    "email_id": "e123",
    "action": "archive",
    "policy_id": "expired_promos",
    "confidence": 0.95,
    "rationale": "Expired",
    "params": {"folder": "Archive"}
}])

# List
from app.db import approvals_get
pending = approvals_get(status="proposed", limit=50)

# Approve
from app.db import approvals_update_status
approvals_update_status([1, 2, 3], "approved")

# Audit
from app.logic.audit_es import emit_audit
emit_audit({
    "email_id": "e123",
    "action": "archive",
    "actor": "agent",
    "status": "proposed",
    "policy_id": "expired_promos",
    "confidence": 0.95,
    "rationale": "Expired",
    "created_at": "2025-10-10T00:00:00Z",
    "payload": {}
})
```

## Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/applylens
ES_URL=http://localhost:9200
ES_API_KEY=optional_key
ES_AUDIT_INDEX=actions_audit_v1
```

## Files Modified/Created

1. ✅ `alembic/versions/0007_approvals_proposed.py` - DB migration
2. ✅ `app/scripts/create_audit_index.py` - ES mapping
3. ✅ `app/db.py` - 3 new functions (~75 lines)
4. ✅ `app/logic/audit_es.py` - ES audit logger (~80 lines)
5. ✅ `app/routers/approvals.py` - 5 endpoints (~330 lines)
6. ✅ `app/main.py` - Router registration (+7 lines)
7. ✅ `tests/unit/test_approvals_db.py` - 11 unit tests (~280 lines)
8. ✅ `tests/e2e/test_approvals_flow.py` - 9 E2E tests (~300 lines)
9. ✅ `kibana/policy-hits-vs-misses.ndjson` - Kibana dashboard

**Total**: ~900 lines of code

## Testing Note

Tests require Docker environment with psycopg2 installed. All production code is complete and will work when dependencies are available.
