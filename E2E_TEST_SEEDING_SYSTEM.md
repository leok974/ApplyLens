# E2E Test Data Seeding System

## Overview

This document describes the dev-only endpoint and Playwright helper that automatically seed test data for E2E tests, ensuring tests never fail due to empty inbox.

## System Components

### 1. Backend: Dev Seed Endpoint

**File**: `services/api/app/routers/dev_seed.py`

**Endpoint**: `POST /api/dev/seed-threads`

**Security**:
- Only available when `ALLOW_DEV_ROUTES=1` environment variable is set
- Returns 403 Forbidden if environment variable not set
- Requires authenticated user (uses existing auth dependency)

**Request Model**:
```python
class SeedThread(BaseModel):
    thread_id: str
    subject: str
    from_addr: str
    risk_level: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    summary_headline: str
    summary_details: List[str]
```

**Response Model**:
```python
class SeedResult(BaseModel):
    ok: bool
    count: int
```

**Example Usage**:
```bash
curl -X POST http://localhost:8000/api/dev/seed-threads \
  -H "Content-Type: application/json" \
  -d '[
    {
      "thread_id": "test-1",
      "subject": "Interview Request",
      "from_addr": "recruiter@example.com",
      "risk_level": "LOW",
      "summary_headline": "Recruiter asking to schedule call",
      "summary_details": ["Waiting on availability"]
    }
  ]'
```

### 2. Frontend: Playwright Seed Helper

**File**: `tests/e2e/utils/seedInbox.ts`

**Function**: `seedInboxThreads(request: APIRequestContext)`

**Features**:
- Automatically seeds 3 mock threads before each test
- Safe to call in production (no-ops when `PROD=1`)
- Handles 403/404 gracefully (logs and continues)
- Returns seed count on success

**Mock Data Seeded**:
1. **Test Thread 1**: Interview invite (LOW risk)
2. **Test Thread 2**: Offer details (LOW risk)
3. **Test Thread 3**: Application status (MEDIUM risk)

Each thread includes:
- Unique thread_id
- Subject line
- From address
- Risk level
- Summary headline
- Summary details (3 bullet points)

**Example Usage in Tests**:
```typescript
import { seedInboxThreads } from "./utils/seedInbox";

test.describe("My Test Suite", () => {
  test.beforeEach(async ({ request }) => {
    await seedInboxThreads(request);
  });

  test("my test", async ({ page }) => {
    // Inbox now has 3 threads seeded
    await page.goto("/inbox");
    // ... test code
  });
});
```

---

## Setup Instructions

### Local Development

1. **Enable Dev Routes**:
   ```bash
   # In your .env file or shell:
   export ALLOW_DEV_ROUTES=1
   ```

2. **Start Backend**:
   ```bash
   cd services/api
   uvicorn app.main:app --reload
   ```

3. **Run Tests**:
   ```bash
   cd ../..
   npx playwright test tests/e2e/thread-viewer-*.spec.ts
   ```

   Tests will automatically:
   - Call `/api/dev/seed-threads` before each test
   - Seed 3 mock threads
   - Run test assertions against seeded data

### CI/CD Configuration

**Development/Staging**:
```yaml
# .github/workflows/e2e-tests.yml
- name: Run E2E Tests
  run: npx playwright test
  env:
    ALLOW_DEV_ROUTES: "1"
```

**Production** (seed disabled):
```yaml
- name: Run Production-Safe E2E Tests
  run: npx playwright test
  env:
    PROD: "1"  # Disables seeding and mutating tests
```

---

## Updated Test Files

All thread viewer test files now include seed helper:

### 1. thread-viewer-basic-context.spec.ts ✅
```typescript
test.beforeEach(async ({ request }) => {
  await seedInboxThreads(request);
});
```

### 2. thread-viewer-triage-navigation.spec.ts ✅
```typescript
test.beforeEach(async ({ request }) => {
  await seedInboxThreads(request);
});
```

### 3. thread-viewer-bulk-mode.spec.ts ✅
```typescript
test(SKIP_MUTATING ? "skipped" : "bulk actions", async ({ page, request }) => {
  test.skip(SKIP_MUTATING, "Mutating test");
  await seedInboxThreads(request);
  // ... test code
});
```

### 4. thread-summary-feedback.spec.ts ✅
```typescript
test.beforeEach(async ({ request }) => {
  await seedInboxThreads(request);
});
```

### 5. thread-summary-feedback-no-regression.spec.ts ✅
```typescript
test.beforeEach(async ({ request }) => {
  await seedInboxThreads(request);
});
```

---

## Production Safety

### Seed Helper Guards

The `seedInboxThreads` function has multiple safety mechanisms:

1. **Environment Check**:
   ```typescript
   if (process.env.PROD === "1") {
     console.log("[SEED] Skipping seed in production");
     return;
   }
   ```

2. **403 Handling** (dev routes disabled):
   ```typescript
   if (resp.status() === 403) {
     console.log("[SEED] Dev routes disabled");
     return;  // Don't fail test
   }
   ```

3. **404 Handling** (endpoint not found):
   ```typescript
   if (resp.status() === 404) {
     console.log("[SEED] Dev seed endpoint not found");
     return;  // Don't fail test
   }
   ```

4. **Error Handling**:
   ```typescript
   try {
     // seed logic
   } catch (error) {
     console.error("[SEED] Error seeding:", error);
     // Don't fail - tests may pass with real data
   }
   ```

### Backend Guards

The FastAPI endpoint has security guards:

1. **Environment Variable Check**:
   ```python
   if os.getenv("ALLOW_DEV_ROUTES") != "1":
       raise HTTPException(status_code=403, detail="dev routes disabled")
   ```

2. **Authentication Required**:
   ```python
   async def seed_threads(
       threads: List[SeedThread],
       user_email: str = Depends(get_current_user_email),  # Auth required
   ):
   ```

3. **Conditional Registration**:
   ```python
   # In main.py
   if os.getenv("ALLOW_DEV_ROUTES") == "1":
       app.include_router(dev_seed.router)
   ```

---

## Implementation Status

### Backend
- ✅ `dev_seed.py` router created
- ✅ Registered in `main.py` with environment guard
- ✅ Security guards in place (ALLOW_DEV_ROUTES check)
- ⏳ TODO: Implement actual data insertion (currently stub)

### Frontend
- ✅ `seedInbox.ts` helper created
- ✅ 3 mock threads defined
- ✅ Production safety guards
- ✅ Error handling for 403/404/network errors

### Test Files
- ✅ `thread-viewer-basic-context.spec.ts` - Uses seed helper
- ✅ `thread-viewer-triage-navigation.spec.ts` - Uses seed helper
- ✅ `thread-viewer-bulk-mode.spec.ts` - Uses seed helper
- ✅ `thread-summary-feedback.spec.ts` - Uses seed helper
- ✅ `thread-summary-feedback-no-regression.spec.ts` - Uses seed helper

---

## Next Steps

### Immediate (Required for Tests to Pass)

1. **Implement Backend Seeding Logic**:

   In `services/api/app/routers/dev_seed.py`, implement the TODO:

   ```python
   # Example for Elasticsearch-backed inbox:
   from app.es import es_client

   for thread in threads:
       es_client.index(
           index="emails",
           id=thread.thread_id,
           body={
               "message_id": thread.thread_id,
               "subject": thread.subject,
               "from_email": thread.from_addr,
               "user_email": user_email,
               "risk_level": thread.risk_level.lower(),
               "archived": False,
               "quarantined": False,
               "summary": {
                   "headline": thread.summary_headline,
                   "details": thread.summary_details,
               },
               "timeline": [
                   {
                       "actor": thread.from_addr,
                       "ts": "2025-01-15T10:30:00Z",
                       "note": "Initial message received",
                       "kind": "received",
                   }
               ],
               "received_at": "2025-01-15T10:30:00Z",
               "category": "interview" if "interview" in thread.subject.lower() else "offer",
           }
       )
   ```

2. **Set Environment Variable**:
   ```bash
   export ALLOW_DEV_ROUTES=1
   ```

3. **Run Tests**:
   ```bash
   npx playwright test tests/e2e/thread-viewer-*.spec.ts
   ```

### Short-term (Nice to Have)

1. **Add More Mock Threads**:
   - Different risk levels (HIGH, CRITICAL)
   - Different categories (rejection, application_receipt)
   - Threads with/without summaries
   - Threads with different timeline events

2. **Add Seed Cleanup**:
   ```typescript
   test.afterEach(async ({ request }) => {
     await cleanupSeededThreads(request);
   });
   ```

3. **Add Seed Validation**:
   - Verify seeded threads appear in inbox
   - Check thread details match seed data
   - Validate risk analysis present

### Long-term (Advanced)

1. **Parameterized Seeding**:
   ```typescript
   await seedInboxThreads(request, {
     count: 10,
     riskLevels: ["HIGH", "CRITICAL"],
     includeTimeline: true,
   });
   ```

2. **Seed Fixtures Library**:
   - Pre-defined thread templates
   - Category-specific threads (interview, offer, rejection)
   - Edge cases (missing data, long subjects, etc.)

3. **Seed State Management**:
   - Track seeded threads per test session
   - Cleanup only user's seeded data
   - Avoid conflicts between parallel tests

---

## Troubleshooting

### Tests Still Fail with "No Rows"

**Symptom**: Tests timeout waiting for `[data-testid="thread-row"]`

**Possible Causes**:
1. `ALLOW_DEV_ROUTES` not set
2. Backend seeding logic not implemented
3. Authentication issues
4. Elasticsearch/database connection issues

**Debug Steps**:
```bash
# 1. Check environment variable
echo $ALLOW_DEV_ROUTES  # Should output: 1

# 2. Test endpoint manually
curl -X POST http://localhost:8000/api/dev/seed-threads \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -H "Content-Type: application/json" \
  -d '[{"thread_id":"test","subject":"Test","from_addr":"test@example.com","risk_level":"LOW","summary_headline":"Test","summary_details":["Test"]}]'

# 3. Check backend logs
# Look for: "[DEV SEED] inbox seeding X threads for user@example.com"

# 4. Check database/ES
# Verify documents were actually created
```

### Seed Returns 403 Forbidden

**Cause**: `ALLOW_DEV_ROUTES` environment variable not set

**Fix**:
```bash
export ALLOW_DEV_ROUTES=1
# Restart backend
```

### Seed Returns 404 Not Found

**Cause**: Router not registered in `main.py`

**Fix**: Verify `main.py` includes:
```python
if os.getenv("ALLOW_DEV_ROUTES") == "1":
    from .routers import dev_seed
    app.include_router(dev_seed.router)
```

### Seed Returns 401 Unauthorized

**Cause**: No authentication cookie/token

**Fix**: Tests should use Playwright's `storageState` to persist auth:
```typescript
// playwright.config.ts
use: {
  storageState: "playwright/.auth/user.json",
}
```

---

## Security Considerations

### Production Deployment

**CRITICAL**: Never set `ALLOW_DEV_ROUTES=1` in production!

**Deployment Checklist**:
- [ ] Production `.env` does NOT contain `ALLOW_DEV_ROUTES`
- [ ] CI/CD production jobs use `PROD=1` environment variable
- [ ] Dev seed router returns 403 in production
- [ ] Seed helper no-ops in production (`PROD=1`)

### Why Two Layers of Guards?

1. **Backend Guard** (`ALLOW_DEV_ROUTES`):
   - Prevents endpoint from being registered
   - Returns 403 if accidentally called
   - Protects against direct API access

2. **Frontend Guard** (`PROD=1`):
   - Prevents tests from calling endpoint
   - Skips mutating tests
   - Allows production-safe tests to run

**Defense in Depth**: Even if one guard fails, the other protects production.

---

## Summary

✅ **Backend endpoint created** (`/api/dev/seed-threads`)
✅ **Playwright helper created** (`seedInboxThreads`)
✅ **All 5 test files updated** to use seed helper
✅ **Production safety guards** in place (dual-layer)
✅ **Documentation complete**

**Next Step**: Implement backend seeding logic (insert to ES/DB) and set `ALLOW_DEV_ROUTES=1` to enable automatic test data seeding.

**Result**: Tests will never fail due to empty inbox. Seed system automatically provides 3 mock threads before each test run.
