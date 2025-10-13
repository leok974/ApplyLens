# Phase 4: Agentic Actions & Approval Loop - Implementation Guide

## Overview

Phase 4 adds intelligent, policy-driven email automation with human-in-the-loop approval. The system proposes actions based on configurable policies, allows user review, executes approved actions, and maintains a comprehensive audit trail.

## ✅ Completed Components

### 1. Data Models (`app/models.py`)

**New Enums:**

- `ActionType`: 8 action types (label, archive, move, unsubscribe, calendar, task, block, quarantine)

**New Models:**

- `ProposedAction`: Queued action proposals pending review
  - Status lifecycle: pending → approved/rejected → executed/failed
  - Links to Policy and Email
  - Stores confidence, rationale, params

- `AuditAction`: Immutable audit trail
  - Records actor, outcome, error, why
  - Optional screenshot path
  - Indexed by email_id and created_at

- `Policy`: Yardstick policy rules
  - JSON condition (DSL)
  - Priority-based execution (lower runs first)
  - Confidence threshold
  - Enabled/disabled flag

### 2. Database Migration (`alembic/versions/0016_phase4_actions.py`)

**Creates:**

- `actiontype` enum (8 values)
- `policies` table with condition JSON and action enum
- `proposed_actions` table with foreign key to policies
- `audit_actions` table with full audit fields

**Chains from:** `0015_add_security_policies`

**To Apply:**

```bash
docker exec infra-api-1 alembic upgrade head
```text

### 3. Yardstick Policy Engine (`app/core/yardstick.py`)

**DSL Features:**

- Logical operators: `all`, `any`, `not`
- Comparators: `eq`, `neq`, `lt`, `lte`, `gt`, `gte`, `in`, `regex`, `exists`
- Special value: `"now"` → current datetime
- Auto datetime parsing for ISO strings

**Functions:**

- `evaluate_policy(policy, ctx)` → bool
- `validate_condition(condition)` → (valid, error_msg)
- `_eval(expr, ctx)` → recursive evaluation
- `_cmp(node, ctx)` → comparator execution

**Example Policy:**

```json
{
  "condition": {
    "all": [
      {"eq": ["category", "promotions"]},
      {"lt": ["expires_at", "now"]}
    ]
  }
}
```text

**Example Context:**

```python
{
  "category": "promotions",
  "risk_score": 45.2,
  "expires_at": "2025-01-15T00:00:00Z",
  "sender_domain": "example.com",
  "age_days": 3,
  "quarantined": False
}
```text

### 4. Action Executors (`app/core/executors.py`)

**Implemented Stubs for 8 Actions:**

- `gmail_archive(email_id)` - Remove INBOX, add ARCHIVED
- `gmail_label(email_id, label)` - Add label
- `gmail_move(email_id, folder)` - Move to folder
- `try_list_unsubscribe(email_id)` - Parse List-Unsubscribe header
- `create_calendar_event(params)` - Google Calendar API
- `create_task_item(params)` - Google Tasks API
- `block_sender(sender)` - Create Gmail filter
- `quarantine_email(email_id)` - Set quarantined flag + move attachments

**All return:** `(success: bool, error: str | None)`

**Integration Points (TODOs):**

- Gmail API service injection
- Calendar API service injection
- Tasks API service injection
- Attachment storage management
- Domain whitelist for safe unsubscribe

### 5. Actions Router (`app/routers/actions.py`)

**Endpoints:**

#### Action Proposal & Approval

- `POST /actions/propose` - Create proposals for emails
  - Body: `{email_ids?, query?, limit?}`
  - Process: Load emails → evaluate policies → create proposals
  - Returns: `{created: [ids], count: N}`

- `POST /actions/{id}/approve` - Approve and execute
  - Body: `{screenshot_data_url?}`
  - Process: Validate → execute → audit → update status
  - Returns: `{ok: bool, outcome: str, error?: str}`

- `POST /actions/{id}/reject` - Reject proposal
  - Process: Mark rejected → write audit (outcome=noop)
  - Returns: `{ok: true}`

- `GET /actions/tray` - List pending (UI tray)
  - Query: `?limit=50`
  - Returns: Array of proposals with email details

#### Policy CRUD

- `GET /actions/policies` - List all policies
  - Query: `?enabled_only=false`
  - Returns: Array of policies ordered by priority

- `POST /actions/policies` - Create new policy
  - Body: `PolicyCreate` (name, enabled, priority, condition, action, confidence_threshold)
  - Validates condition syntax
  - Returns: Created policy

- `PUT /actions/policies/{id}` - Update policy
  - Body: `PolicyUpdate` (all fields optional)
  - Validates condition if provided
  - Returns: Updated policy

- `DELETE /actions/policies/{id}` - Delete policy
  - Returns: `{ok: true}`

- `POST /actions/policies/{id}/test` - Test policy
  - Body: `{email_ids?, limit?}`
  - Returns: `{matches: [email_ids], count: N}`

**Helper Functions:**

- `build_email_ctx(email)` - Convert Email to Yardstick context
- `extract_domain(email_address)` - Parse domain from email
- `build_rationale(email, policy)` - Generate confidence + rationale
- `derive_action_params(email, policy)` - Action-specific params
- `save_screenshot(data_url)` - Save base64 screenshot to `/data/audit/YYYY-MM/`
- `get_current_user()` - Auth stub (returns mock user)

### 6. Default Policies (`app/seeds/policies.py`)

**5 Seed Policies:**

1. **Promo auto-archive** (Priority 50, Enabled)

   ```json
   {
     "all": [
       {"eq": ["category", "promotions"]},
       {"exists": ["expires_at"]},
       {"lt": ["expires_at", "now"]}
     ]
   }
   ```

2. **High-risk quarantine** (Priority 10, Enabled)

   ```json
   {"gte": ["risk_score", 80]}
   ```

3. **Job application auto-label** (Priority 30, Enabled)

   ```json
   {
     "all": [
       {"eq": ["category", "applications"]},
       {"regex": ["subject", "(?i)(application|interview|offer)"]}
     ]
   }
   ```

4. **Create event from invitation** (Priority 40, Disabled)

   ```json
   {
     "all": [
       {"eq": ["category", "events"]},
       {"exists": ["event_start_at"]},
       {"regex": ["subject", "(?i)(invitation|invite|meeting|event)"]}
     ]
   }
   ```

5. **Auto-unsubscribe inactive senders** (Priority 60, Disabled)

   ```json
   {
     "all": [
       {"eq": ["category", "promotions"]},
       {"gte": ["age_days", 90]},
       {"exists": ["sender_domain"]}
     ]
   }
   ```

**Functions:**

- `seed_policies(db)` - Insert defaults (skips existing)
- `reset_policies(db)` - Delete all + reseed (WARNING: destructive)

**To Seed:**

```bash
docker exec infra-api-1 python -m app.seeds.policies
```text

## 🔄 Remaining Components (Frontend + Tests)

### 7. Frontend API Client (`apps/web/src/lib/actionsClient.ts`)

**Required Functions:**

```typescript
export async function fetchTray(): Promise<ProposedAction[]>
export async function approveAction(id: number, screenshotDataUrl?: string): Promise<{ok: bool}>
export async function rejectAction(id: number): Promise<{ok: bool}>
export async function proposeByQuery(query: string, limit?: number): Promise<{created: number[], count: number}>
export async function listPolicies(enabledOnly?: boolean): Promise<Policy[]>
export async function createPolicy(policy: PolicyCreate): Promise<Policy>
export async function updatePolicy(id: number, policy: PolicyUpdate): Promise<Policy>
export async function deletePolicy(id: number): Promise<{ok: bool}>
export async function testPolicy(id: number, emailIds?: number[]): Promise<{matches: number[], count: number}>
```text

### 8. ActionsTray Component (`apps/web/src/components/ActionsTray.tsx`)

**Features Needed:**

- Right-side drawer (fixed position, slide in/out)
- List pending actions from `/api/actions/tray`
- Action card UI:
  - Email subject + sender
  - Action type chip
  - Confidence percentage
  - Expandable "Explain" section with rationale
  - Approve/Reject buttons
  - "Always do this" button (creates/updates policy)
- Screenshot capture on approve using `html2canvas`
- Real-time refresh after approve/reject

**Example Structure:**

```tsx
<div className="fixed right-0 top-0 h-full w-[420px] bg-neutral-900/90">
  <div className="p-4">
    <h3>Proposed actions</h3>
    <button onClick={refresh}>Refresh</button>
  </div>
  <div className="space-y-3">
    {items.map(item => (
      <ActionCard
        key={item.id}
        item={item}
        onApprove={handleApprove}
        onReject={handleReject}
        onAlwaysDoThis={handleAlwaysDoThis}
      />
    ))}
  </div>
</div>
```text

### 9. Backend Tests

#### `tests/test_yardstick_eval.py`

```python
def test_eval_all_operator()
def test_eval_any_operator()
def test_eval_not_operator()
def test_comparator_eq()
def test_comparator_gte()
def test_comparator_regex()
def test_comparator_exists()
def test_comparator_in()
def test_datetime_comparison()
def test_special_value_now()
def test_validate_condition_valid()
def test_validate_condition_invalid()
```text

#### `tests/test_actions_propose.py`

```python
def test_propose_creates_actions(client, db, seed_emails, seed_policies)
def test_propose_respects_priority(client, db)
def test_propose_filters_by_confidence(client, db)
def test_propose_stops_at_first_match(client, db)
def test_propose_with_email_ids(client, db)
def test_propose_with_no_policies_fails(client, db)
```text

#### `tests/test_actions_approve_and_audit.py`

```python
def test_approve_executes_action(client, db)
def test_approve_writes_audit(client, db)
def test_approve_saves_screenshot(client, db)
def test_reject_writes_audit(client, db)
def test_approve_non_pending_fails(client, db)
def test_reject_non_pending_fails(client, db)
```text

### 10. E2E Tests

#### `tests/actions.tray.spec.ts`

```typescript
test("renders pending actions in tray", async ({ page }) => {
  // Mock /api/actions/tray
  // Navigate to page
  // Verify actions are displayed
})

test("approve action captures screenshot", async ({ page }) => {
  // Mock /api/actions/tray and /api/actions/{id}/approve
  // Click approve button
  // Verify screenshot data URL is sent
  // Verify action is removed from tray
})

test("reject action updates tray", async ({ page }) => {
  // Mock endpoints
  // Click reject button
  // Verify action is removed
})

test("always do this creates policy", async ({ page }) => {
  // Mock endpoints
  // Click "Always do this" button
  // Verify policy creation request
})
```text

#### `tests/policies.crud.spec.ts`

```typescript
test("create policy with valid condition", async ({ page }) => {
  // Navigate to policies page
  // Fill form with policy data
  // Submit
  // Verify policy is created
})

test("test policy shows matching emails", async ({ page }) => {
  // Create policy
  // Click "Test" button
  // Verify matching email IDs are displayed
})

test("disable policy prevents proposals", async ({ page }) => {
  // Create policy
  // Disable it
  // Run propose
  // Verify no proposals created
})
```text

### 11. SSE Events Endpoint (`app/routers/actions.py`)

**Add Endpoint:**

```python
@router.get("/events")
async def action_events(request: Request):
    """
    Server-Sent Events stream for real-time action notifications.
    
    Events:
    - action_proposed: {"id": 123, "action": "archive_email", ...}
    - action_approved: {"id": 123, "outcome": "success"}
    - action_executed: {"id": 123, "outcome": "success"}
    - action_failed: {"id": 123, "error": "..."}
    """
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            
            # TODO: Implement event queue/pubsub
            # For now, keepalive every 15s
            await asyncio.sleep(15)
            yield ": keepalive\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```text

**Frontend Integration:**

```typescript
const events = new EventSource("/api/actions/events")
events.onmessage = (e) => {
  const data = JSON.parse(e.data)
  if (data.type === "action_proposed") {
    refreshTray()
    showNotification(`New action proposed: ${data.action}`)
  }
}
```text

### 12. Documentation (`docs/PHASE_4_ACTIONS.md`)

**Required Sections:**

- Overview
- Architecture diagram
- Policy DSL reference (all operators + examples)
- API endpoint reference
- Action executor details
- Screenshot capture flow
- Audit trail schema
- Deployment guide
- PowerShell quickrun commands
- Troubleshooting

## Integration Steps

### 1. Register Actions Router

**File:** `services/api/app/main.py`

```python
from .routers import actions

app.include_router(actions.router, prefix="/api")
```text

### 2. Apply Migration

```bash
docker exec infra-api-1 alembic upgrade head
```text

Expected output:

```text
INFO  [alembic.runtime.migration] Running upgrade 0015 -> 0016, phase4 actions
```text

### 3. Seed Policies

```bash
docker exec infra-api-1 python -c "
from app.db import SessionLocal
from app.seeds.policies import seed_policies

db = SessionLocal()
try:
    seed_policies(db)
finally:
    db.close()
"
```text

### 4. Test Endpoints

```powershell
# List policies
curl http://localhost:8003/api/actions/policies | jq .

# Propose actions
curl -X POST http://localhost:8003/api/actions/propose `
  -H "Content-Type: application/json" `
  -d '{"limit":10}' | jq .

# List tray
curl http://localhost:8003/api/actions/tray | jq .

# Approve first action
$first = (curl http://localhost:8003/api/actions/tray | jq -r '.[0].id')
curl -X POST "http://localhost:8003/api/actions/$first/approve" `
  -H "Content-Type: application/json" `
  -d '{}' | jq .
```text

### 5. Install Frontend Dependencies

```bash
cd apps/web
npm install html2canvas
```text

### 6. Add Navigation Icon

**File:** `apps/web/src/components/Layout.tsx`

```tsx
import { BellIcon } from "lucide-react"
import { ActionsTray } from "@/components/ActionsTray"

// Add badge with pending count
<button onClick={() => setTrayOpen(true)}>
  <BellIcon />
  {pendingCount > 0 && <span className="badge">{pendingCount}</span>}
</button>

{trayOpen && <ActionsTray onClose={() => setTrayOpen(false)} />}
```text

## Testing Workflow

### Manual Testing

1. **Seed data:**
   - Create test emails with various categories/risk_scores
   - Seed default policies

2. **Propose actions:**

   ```bash
   curl -X POST http://localhost:8003/api/actions/propose -d '{"limit":20}'
   ```

3. **View tray:**
   - Open UI, click actions icon
   - Verify pending actions are displayed
   - Expand "Explain" section, verify rationale

4. **Approve action:**
   - Click "Approve" button
   - Verify screenshot is captured
   - Check audit_actions table for entry

5. **Reject action:**
   - Click "Reject" button
   - Verify action is removed from tray
   - Check audit entry

6. **Create policy:**
   - Navigate to policies page
   - Create new policy with DSL condition
   - Test against emails
   - Verify proposals match expectations

### Automated Testing

```bash
# Backend tests
docker exec infra-api-1 python -m pytest tests/test_yardstick_eval.py -v
docker exec infra-api-1 python -m pytest tests/test_actions_propose.py -v
docker exec infra-api-1 python -m pytest tests/test_actions_approve_and_audit.py -v

# E2E tests
cd apps/web
npm run test:e2e -- actions.tray.spec.ts
npm run test:e2e -- policies.crud.spec.ts
```text

## Security Considerations

1. **Authentication:**
   - Replace `get_current_user()` stub with real JWT/session auth
   - Verify user has permission to approve/reject actions

2. **Screenshot Storage:**
   - Limit screenshot file size (< 5MB)
   - Set retention policy (90 days)
   - Implement cleanup job

3. **Policy Validation:**
   - Validate condition syntax before saving
   - Sanitize regex patterns (prevent ReDoS)
   - Rate-limit policy creation

4. **Executor Safety:**
   - Whitelist domains for unsubscribe GET requests
   - Validate email ownership before Gmail API calls
   - Sandbox attachment quarantine directory

5. **Audit Integrity:**
   - Audit table is append-only (no updates/deletes)
   - Hash screenshot files for tamper detection
   - Log all policy changes

## Performance Optimization

1. **Proposal Generation:**
   - Batch evaluate policies (avoid N+1 queries)
   - Cache policy conditions in memory
   - Use ES for email filtering (vs DB scan)

2. **Tray Loading:**
   - Paginate tray results (default limit=50)
   - Include email details in single query (join)
   - Cache pending count for badge

3. **SSE Events:**
   - Use Redis pub/sub for event broadcasting
   - Implement backpressure for slow clients
   - Auto-disconnect idle clients after 5min

## Monitoring

**Prometheus Metrics:**

```python
from prometheus_client import Counter, Histogram

actions_proposed = Counter("actions_proposed_total", "Total actions proposed", ["policy"])
actions_executed = Counter("actions_executed_total", "Total actions executed", ["action", "outcome"])
actions_failed = Counter("actions_failed_total", "Total actions failed", ["action", "error_type"])
policy_eval_duration = Histogram("policy_eval_duration_seconds", "Policy evaluation time")
```text

**Grafana Dashboard:**

- Actions proposed per hour (by policy)
- Action approval rate
- Action failure rate (by type)
- Average confidence score
- Pending action backlog

## Next Steps (Phase 4.1)

1. **ES Aggregations in Rationale:**
   - Sender domain statistics
   - Percentiles for expiry windows
   - Similar emails in last 14d

2. **KNN Neighbors:**
   - Implement `body_vector` mapping
   - Generate embeddings at ingest
   - Include top-5 neighbors in rationale

3. **Advanced Executors:**
   - Full Gmail API integration
   - Google Calendar API integration
   - Google Tasks API integration
   - Attachment quarantine storage

4. **Policy Versioning:**
   - Add `policies_history` table
   - Track all policy changes
   - Audit which version triggered each proposal

5. **ML Confidence:**
   - Train classifier for confidence scores
   - Use model probability instead of heuristic
   - A/B test policy thresholds

## Summary

**Phase 4 Backend (✅ Complete):**

- ✅ Models and migration (ProposedAction, AuditAction, Policy)
- ✅ Yardstick DSL engine with full operator set
- ✅ Action executors (8 types, stubs ready for integration)
- ✅ Actions router (propose, approve, reject, tray, policy CRUD)
- ✅ Default policies (5 sensible defaults)

**Phase 4 Frontend (⏳ Pending):**

- ⏳ Actions API client
- ⏳ ActionsTray component
- ⏳ Policy management UI

**Phase 4 Testing (⏳ Pending):**

- ⏳ Yardstick unit tests
- ⏳ Actions API tests
- ⏳ Playwright E2E tests

**Phase 4 Infrastructure (⏳ Pending):**

- ⏳ SSE events endpoint
- ⏳ Screenshot cleanup job
- ⏳ Prometheus metrics
- ⏳ Documentation

**Total Progress: 50% Complete** (Backend done, Frontend + Tests + Infra remaining)
