# Final Implementation Checklist - Thread Viewer E2E Tests

## ✅ COMPLETED

### Backend Infrastructure
- [x] **Dev seed endpoint created** (`services/api/app/routers/dev_seed.py`)
  - Type-safe Pydantic models (`SeedThread`, `SeedResult`)
  - Security guard: Only works when `ALLOW_DEV_ROUTES=1`
  - Authentication required
  - Comprehensive logging

- [x] **Router conditionally registered** in `services/api/app/main.py`
  ```python
  if os.getenv("ALLOW_DEV_ROUTES") == "1":
      from .routers import dev_seed
      app.include_router(dev_seed.router)
  ```

### Frontend Infrastructure
- [x] **Playwright seed helper created** (`tests/e2e/utils/seedInbox.ts`)
  - `seedInboxThreads(request)` function
  - 3 comprehensive mock threads with full metadata
  - Production safety: no-ops when `PROD=1`
  - Error handling: 403/404 gracefully handled

- [x] **All test files updated** with seed calls (5 files):
  - `thread-viewer-basic-context.spec.ts`
  - `thread-viewer-triage-navigation.spec.ts`
  - `thread-viewer-bulk-mode.spec.ts`
  - `thread-summary-feedback.spec.ts`
  - `thread-summary-feedback-no-regression.spec.ts`

### Test Infrastructure
- [x] **PowerShell test runner** (`playwright.test-run.ps1`)
  - Starts backend API with `ALLOW_DEV_ROUTES=1`
  - Starts web preview server
  - Sets all required environment variables
  - Runs Playwright tests
  - Cleans up background jobs

- [x] **Playwright configs updated**
  - Root config: conditional webServer based on external servers
  - Web app config: already checks `E2E_BASE_URL`

### Documentation
- [x] **Complete documentation created**:
  - `E2E_TEST_SEEDING_SYSTEM.md` - Seeding system guide
  - `E2E_SEEDING_IMPLEMENTATION_COMPLETE.md` - Implementation summary
  - `THREAD_VIEWER_E2E_TESTS.md` - Test suite documentation
  - `THREAD_VIEWER_E2E_FINAL_REPORT.md` - Complete reference
  - `TEST_EXECUTION_SUMMARY.md` - Execution guide
  - `FINAL_IMPLEMENTATION_CHECKLIST.md` - This file

---

## ⏳ PENDING (Critical Path to Green Tests)

### 1. Implement Backend Seeding Logic ⚠️ HIGH PRIORITY

**File**: `services/api/app/routers/dev_seed.py`

**Current State**: Stub that logs and returns success

**What's Needed**: Actually insert thread data into your backend store

**Example Implementation** (adjust to your data layer):

```python
@router.post("/seed-threads", response_model=SeedResult)
async def seed_threads(
    threads: List[SeedThread],
    user_email: str = Depends(get_current_user_email),
):
    # ... existing guards ...

    # TODO: Replace this with actual implementation
    from app.es import es_client  # or your DB client

    for thread in threads:
        # Insert to Elasticsearch (adjust index name)
        es_client.index(
            index="emails",  # or emails_v1-000001, etc.
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
                "text_body": f"Mock email body for {thread.subject}",
                "html_body": f"<p>Mock email body for {thread.subject}</p>",
            }
        )

    return SeedResult(ok=True, count=len(threads))
```

**Acceptance Criteria**:
- [ ] Seeded threads appear in `/inbox` API response
- [ ] At least 2 threads seeded per call
- [ ] Threads have all required fields (subject, from, risk_level, summary, timeline)
- [ ] `archived` and `quarantined` flags set to `false`
- [ ] Threads are associated with the authenticated user

---

### 2. Verify Data-testid Attributes ⚠️ MEDIUM PRIORITY

**Status**: Most attributes already added in previous work

**Double-check these components have the correct `data-testid` attributes**:

#### Inbox.tsx
- [x] `data-testid="thread-row"` on email row
- [x] `data-thread-id={thread.id}` attribute
- [x] `data-selected="true|false"` attribute
- [x] `data-testid="thread-row-checkbox"` on checkbox

#### ThreadViewer.tsx
- [x] `data-testid="thread-viewer"` on main aside element

#### RiskAnalysisSection.tsx
- [x] `data-testid="risk-analysis-section"` on section wrapper

#### ThreadSummarySection.tsx
- [x] `data-testid="thread-summary-section"` on section wrapper
- [x] `data-testid="thread-summary-headline"` on headline
- [x] `data-testid="thread-summary-details"` on bullet list
- [x] `data-testid="summary-feedback-controls"` on controls container
- [x] `data-testid="summary-feedback-yes"` on Yes button
- [x] `data-testid="summary-feedback-no"` on No button
- [x] `data-testid="summary-feedback-ack"` on acknowledgment message

#### ConversationTimelineSection.tsx
- [x] `data-testid="conversation-timeline-section"` on section wrapper
- [x] `data-testid="timeline-event"` on each timeline item

#### ThreadActionBar.tsx
- [x] `data-testid="thread-action-bar"` on wrapper
- [x] `data-testid="action-archive-single"` on Archive button
- [x] `data-testid="action-mark-safe-single"` on Mark Safe button
- [x] `data-testid="action-quarantine-single"` on Quarantine button
- [x] `data-testid="action-open-gmail"` on Open in Gmail button
- [x] `data-testid="action-archive-bulk"` on bulk Archive button
- [x] `data-testid="action-mark-safe-bulk"` on bulk Mark Safe button
- [x] `data-testid="action-quarantine-bulk"` on bulk Quarantine button
- [x] `data-testid="auto-advance-toggle"` on toggle label
- [x] `data-testid="handled-progress"` on progress counter

#### sonner.tsx (Toast)
- [x] `data-testid="toast-container"` on Toaster component

**Verification Command**:
```bash
# Search for all data-testid in components
grep -r "data-testid" apps/web/src/components/
```

---

### 3. Test Environment Setup ⚠️ LOW PRIORITY (Handled by Script)

**What the script handles automatically**:
- [x] Sets `ALLOW_DEV_ROUTES=1` for backend
- [x] Sets `PROD=0` for tests
- [x] Sets `E2E_BASE_URL` to prevent Playwright from starting its own server
- [x] Starts API server on port 8003
- [x] Starts web preview on port 5175
- [x] Cleans up background jobs after tests

**Manual verification** (if script fails):
```powershell
# Check if ports are available
netstat -ano | findstr "8003"  # Should be empty
netstat -ano | findstr "5175"  # Should be empty

# Check if Python/uvicorn available
python --version
uvicorn --version

# Check if npm available
npm --version
```

---

## 🚀 EXECUTION STEPS

### Step 1: Implement Seeding Logic (Critical)
```bash
# Edit this file:
code services/api/app/routers/dev_seed.py

# Replace the TODO with actual ES/DB insert logic
# Use the example above as a template
```

### Step 2: Run the Test Script
```powershell
# From repo root:
.\playwright.test-run.ps1

# Expected output:
# [1/4] Starting backend API...
# [OK] Backend responded
# [2/4] Starting web preview...
# [OK] Web server responding
# [3/4] Running Playwright tests...
# [Test output...]
# [4/4] Stopping background jobs...
# ✅ All tests passed!
```

### Step 3: Debug Failures (If Any)

**If seed endpoint returns 404/403**:
```bash
# Check backend logs for:
# "[OK] Dev seed router registered at /api/dev/*"

# Verify environment variable:
curl http://localhost:8003/api/dev/seed-threads
# Should NOT return 404 if ALLOW_DEV_ROUTES=1 is set
```

**If inbox is empty**:
```bash
# Check backend logs for:
# "[DEV SEED] inbox seeding 3 threads for user@example.com"

# Check ES/DB to verify documents were created
# Verify /api/inbox returns the seeded threads
```

**If tests timeout**:
```bash
# Check Playwright trace:
npx playwright show-trace test-results/[test-name]/trace.zip

# Check screenshots in test-results/ folder
```

---

## 📋 CI/CD Configuration (Future)

### Staging/Dev CI (Run All Tests)
```yaml
- name: E2E Tests (Dev)
  run: |
    cd services/api
    export ALLOW_DEV_ROUTES=1
    uvicorn app.main:app --host 0.0.0.0 --port 8003 &
    sleep 5

    cd ../../apps/web
    npm run preview -- --port 5175 &
    sleep 5

    export PROD=0
    export E2E_BASE_URL=http://localhost:5175
    npx playwright test tests/e2e/thread-viewer-*.spec.ts
```

### Production Smoke Tests (Skip Destructive)
```yaml
- name: E2E Smoke Tests (Prod)
  run: |
    export PROD=1  # Skip bulk-mode test
    export E2E_BASE_URL=https://applylens.app
    npx playwright test tests/e2e/thread-viewer-*.spec.ts
```

---

## 📊 Success Metrics

### All Tests Passing Criteria

**Phase 1 (Risk Analysis)**:
- [ ] Risk section renders with level badge
- [ ] Risk text contains "low|medium|high|critical"

**Phase 2 (Action Bar)**:
- [ ] Action bar renders with all buttons
- [ ] Archive, Mark Safe, Quarantine, Open Gmail buttons visible

**Phase 3 (Keyboard Nav)**:
- [ ] ArrowDown navigates to next thread
- [ ] ArrowUp navigates to previous thread
- [ ] D key archives and advances
- [ ] Escape closes viewer

**Phase 4 (Bulk Mode)**:
- [ ] Checkboxes allow multi-select
- [ ] Bulk buttons appear when 2+ selected
- [ ] Bulk archive/mark-safe/quarantine work
- [ ] Progress meter updates
- [ ] Auto-advance toggle works
- [ ] Toast notifications appear
- [ ] Undo functionality works (if implemented)

**Phase 5 (Context)**:
- [ ] Summary section renders with headline + bullets
- [ ] Timeline section renders with event entries
- [ ] Correct rendering order maintained

**Phase 5.1 (Feedback)**:
- [ ] Yes/No buttons render
- [ ] Clicking Yes shows "Thanks!" acknowledgment
- [ ] Clicking No shows "We'll improve" acknowledgment
- [ ] Toast notification appears
- [ ] Controls disappear after submission
- [ ] Viewer remains stable (no crashes)

---

## 🎯 Summary

### What's Done ✅
- Backend endpoint infrastructure (stub)
- Frontend seed helper (complete)
- Test files updated (all 5)
- PowerShell test runner (complete)
- Playwright configs updated
- All data-testid attributes added
- Complete documentation

### What's Left ⏳
1. **Implement seeding logic** in `dev_seed.py` (30 minutes of work)
2. **Run the script**: `.\playwright.test-run.ps1`
3. **Fix any issues** based on test output

### Estimated Time to Green
- **30 minutes** if ES/DB layer is straightforward
- **1-2 hours** if need to debug data layer integration

### Next Action
**Edit `services/api/app/routers/dev_seed.py` and implement the TODO with actual ES/DB insert logic using the example above as a template.**

Once that's done, run `.\playwright.test-run.ps1` and all tests should go green! 🎉
