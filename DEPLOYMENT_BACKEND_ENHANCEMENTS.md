# Backend Enhancement Deployment Guide

## Overview
This guide covers deploying the new security policy system, bulk actions, search filters, and real-time event notifications.

## What's New

### 1. Security Policies CRUD
- **Endpoints:**
  - `GET /api/policy/security` - Fetch policy (creates defaults if missing)
  - `PUT /api/policy/security` - Update policy configuration
- **Database:** New `security_policies` table via migration 0015
- **Features:**
  - Auto-quarantine high-risk emails
  - Auto-archive expired promotional emails
  - Auto-unsubscribe from inactive senders (configurable threshold)

### 2. Bulk Security Actions
- **Endpoints:**
  - `POST /api/security/bulk/rescan` - Re-analyze multiple emails
  - `POST /api/security/bulk/quarantine` - Quarantine multiple emails
  - `POST /api/security/bulk/release` - Release from quarantine
- **Request:** Array of email IDs: `["id1", "id2", "id3"]`
- **Response:** `{updated/quarantined/released: number, total: number}`

### 3. Search Risk Filters
- **Enhanced endpoint:** `GET /api/search/`
- **New parameters:**
  - `risk_min` (0-100): Minimum risk score
  - `risk_max` (0-100): Maximum risk score
  - `quarantined` (bool): Filter by quarantine status

### 4. Real-Time Event Stream
- **Endpoint:** `GET /api/security/events`
- **Protocol:** Server-Sent Events (SSE)
- **Features:**
  - Real-time high-risk email notifications
  - 15-second keepalive
  - Auto-cleanup on disconnect

### 5. Frontend Components
- **SecuritySummaryCard:** Dashboard widget showing security overview
- **API Functions:** `bulkRescan()`, `bulkQuarantine()`, `bulkRelease()`

## Deployment Steps

### Step 1: Apply Database Migration

```bash
# Apply migration 0015 to create security_policies table
docker exec infra-api-1 alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade 0014_add_security_fields -> 0015_add_security_policies, add security policies table
```

### Step 2: Rebuild API Container

```bash
cd D:\ApplyLens\infra
docker compose up -d --build api
```

**What this does:**
- Picks up new policy router
- Loads bulk action endpoints
- Initializes SSE event bus
- Registers search filter parameters

### Step 3: Verify Services

```bash
# Check API logs
docker logs infra-api-1 --tail 50

# Should see lines like:
# INFO:     Application startup complete.
# No errors about missing imports or routers
```

## Testing

### Test 1: Policy Endpoints

```bash
# Get policy (should create defaults)
curl http://localhost:8003/api/policy/security

# Expected response:
# {
#   "autoQuarantineHighRisk": true,
#   "autoArchiveExpiredPromos": true,
#   "autoUnsubscribeInactive": {
#     "enabled": false,
#     "threshold": 10
#   }
# }

# Update policy
curl -X PUT http://localhost:8003/api/policy/security \
  -H "Content-Type: application/json" \
  -d '{
    "auto_quarantine_high_risk": true,
    "auto_archive_expired_promos": false,
    "auto_unsubscribe_inactive": {
      "enabled": true,
      "threshold": 5
    }
  }'
```

### Test 2: Bulk Actions

```bash
# First, get some email IDs from your database
docker exec infra-db-1 psql -U postgres applylens -c \
  "SELECT id FROM emails LIMIT 3;"

# Use those IDs for bulk quarantine
curl -X POST http://localhost:8003/api/security/bulk/quarantine \
  -H "Content-Type: application/json" \
  -d '["email-id-1", "email-id-2", "email-id-3"]'

# Expected response:
# {"quarantined": 3, "total": 3}

# Bulk release
curl -X POST http://localhost:8003/api/security/bulk/release \
  -H "Content-Type: application/json" \
  -d '["email-id-1", "email-id-2", "email-id-3"]'

# Expected response:
# {"released": 3, "total": 3}

# Bulk rescan
curl -X POST http://localhost:8003/api/security/bulk/rescan \
  -H "Content-Type: application/json" \
  -d '["email-id-1", "email-id-2"]'

# Expected response:
# {"updated": 2, "total": 2}
```

### Test 3: Search Filters

```bash
# Search for high-risk emails (score >= 70)
curl "http://localhost:8003/api/search/?q=&risk_min=70"

# Search for quarantined emails
curl "http://localhost:8003/api/search/?q=&quarantined=true"

# Search for safe emails (score <= 30)
curl "http://localhost:8003/api/search/?q=&risk_max=30"

# Combine filters
curl "http://localhost:8003/api/search/?q=invoice&risk_min=50&risk_max=90&quarantined=false"
```

### Test 4: SSE Event Stream

```bash
# Listen to event stream (will keep connection open)
curl -N http://localhost:8003/api/security/events

# You should see keepalive messages every 15 seconds:
# : keepalive
# : keepalive

# When high-risk emails are analyzed, you'll see:
# data: {"type":"high_risk","email_id":"...","score":85,"quarantined":true,"ts":1234567890}
```

### Test 5: Run Automated Tests

```bash
# Run policy CRUD tests
docker exec infra-api-1 python -m pytest tests/test_policy_crud.py -v

# Run bulk action tests
docker exec infra-api-1 python -m pytest tests/test_bulk_actions.py -v

# Run all security tests
docker exec infra-api-1 python -m pytest tests/ -k security -v
```

**Expected output:**
```
tests/test_policy_crud.py::test_get_policy_creates_defaults PASSED
tests/test_policy_crud.py::test_put_policy_roundtrip PASSED
tests/test_policy_crud.py::test_put_policy_partial_update PASSED
tests/test_policy_crud.py::test_put_policy_with_none_unsubscribe PASSED

tests/test_bulk_actions.py::test_bulk_quarantine PASSED
tests/test_bulk_actions.py::test_bulk_release PASSED
tests/test_bulk_actions.py::test_bulk_rescan PASSED
...

============ X passed in Y.YYs ============
```

## Frontend Integration

### SecuritySummaryCard Usage

```typescript
import { SecuritySummaryCard } from "@/components/security/SecuritySummaryCard";

// Add to your dashboard or homepage
<SecuritySummaryCard />
```

### Bulk Action Usage

```typescript
import { bulkRescan, bulkQuarantine, bulkRelease } from "@/lib/securityApi";

// Example: Quarantine selected emails
const selectedIds = ["id1", "id2", "id3"];

try {
  const result = await bulkQuarantine(selectedIds);
  console.log(`Quarantined ${result.quarantined} of ${result.total} emails`);
} catch (error) {
  console.error("Bulk quarantine failed:", error);
}
```

### SSE Event Listener (Optional)

```typescript
// Create apps/web/src/lib/securityEvents.ts
export function subscribeSecurityEvents(
  onEvent: (event: any) => void
): () => void {
  const es = new EventSource("/api/security/events", {
    withCredentials: true,
  });
  
  es.onmessage = (ev) => {
    const event = JSON.parse(ev.data);
    onEvent(event);
  };
  
  es.onerror = (err) => {
    console.error("SSE error:", err);
    es.close();
  };
  
  // Return cleanup function
  return () => es.close();
}

// Usage in component:
React.useEffect(() => {
  const unsubscribe = subscribeSecurityEvents((event) => {
    if (event.type === "high_risk") {
      toast.error(`High-risk email detected: ${event.email_id}`);
    }
  });
  
  return unsubscribe;
}, []);
```

## Database Schema Changes

### New Table: security_policies

```sql
CREATE TABLE security_policies (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(320) UNIQUE,
    auto_quarantine_high_risk BOOLEAN NOT NULL DEFAULT true,
    auto_archive_expired_promos BOOLEAN NOT NULL DEFAULT true,
    auto_unsubscribe_enabled BOOLEAN NOT NULL DEFAULT false,
    auto_unsubscribe_threshold INTEGER NOT NULL DEFAULT 10,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
```

## API Reference

### Policy Endpoints

#### GET /api/policy/security
Fetch security policy. Creates default policy if none exists.

**Response:**
```json
{
  "autoQuarantineHighRisk": true,
  "autoArchiveExpiredPromos": true,
  "autoUnsubscribeInactive": {
    "enabled": false,
    "threshold": 10
  }
}
```

#### PUT /api/policy/security
Update security policy. Upserts (creates if missing).

**Request:**
```json
{
  "auto_quarantine_high_risk": true,
  "auto_archive_expired_promos": false,
  "auto_unsubscribe_inactive": {
    "enabled": true,
    "threshold": 7
  }
}
```

**Response:** Same format as GET

### Bulk Action Endpoints

#### POST /api/security/bulk/rescan
Re-analyze multiple emails.

**Request:** `["id1", "id2", "id3"]`

**Response:** `{"updated": 3, "total": 3}`

#### POST /api/security/bulk/quarantine
Quarantine multiple emails.

**Request:** `["id1", "id2", "id3"]`

**Response:** `{"quarantined": 3, "total": 3}`

#### POST /api/security/bulk/release
Release emails from quarantine.

**Request:** `["id1", "id2", "id3"]`

**Response:** `{"released": 3, "total": 3}`

### Search Filters

#### GET /api/search/
Enhanced with risk filtering.

**New Parameters:**
- `risk_min` (int, 0-100): Minimum risk score
- `risk_max` (int, 0-100): Maximum risk score
- `quarantined` (bool): Filter by quarantine status

**Examples:**
```
/api/search/?q=invoice&risk_min=70
/api/search/?quarantined=true
/api/search/?risk_min=50&risk_max=80&quarantined=false
```

### SSE Event Stream

#### GET /api/security/events
Server-Sent Events stream for real-time notifications.

**Event Format:**
```
data: {"type":"high_risk","email_id":"...","score":85,"quarantined":true,"ts":1234567890}
```

**Keepalive:** `: keepalive` every 15 seconds

**Headers:**
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`

## Troubleshooting

### Migration Fails
```
ERROR: relation "security_policies" already exists
```
**Solution:** Migration already applied. Skip this step.

### Import Errors
```
ModuleNotFoundError: No module named 'app.security.events'
```
**Solution:** Rebuild API container to pick up new files.

### SSE Connection Drops
**Solution:** Check firewall settings, proxy timeouts. SSE requires long-lived connections.

### Bulk Actions Return 0 Updates
**Cause:** Email IDs don't exist in database.
**Solution:** Verify IDs with `SELECT id FROM emails LIMIT 10;`

### Test Failures
```
FAILED test_bulk_actions.py::test_bulk_rescan
```
**Solution:** Check that `Email` model has `raw_body` field for header extraction. Review security analyzer logs.

## Next Steps

1. **Enable Auto-Policies:** Turn on auto-quarantine and auto-archive in settings
2. **Monitor SSE Events:** Implement frontend notification toast system
3. **Build Bulk UI:** Add toolbar buttons for bulk operations in email list
4. **Add Risk Filters:** Implement search filter chips in UI
5. **Performance Tuning:** Monitor bulk rescan performance with large ID lists

## Rollback Plan

If issues occur:

```bash
# Rollback migration
docker exec infra-api-1 alembic downgrade -1

# Revert to previous API version
cd D:\ApplyLens\infra
git checkout <previous-commit>
docker compose up -d --build api
```

## Support

For issues or questions:
1. Check API logs: `docker logs infra-api-1 --tail 100`
2. Check database: `docker exec infra-db-1 psql -U postgres applylens`
3. Review test failures for clues
4. Verify all environment variables are set correctly
