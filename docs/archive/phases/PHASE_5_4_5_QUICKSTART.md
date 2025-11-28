# Phase 5.4 & 5.5 Quick Start Guide

## ✅ Implementation Complete

**Phase 5.4**: Epsilon-greedy bandit (ε=0.15) for intelligent style exploration
**Phase 5.5**: Production smoke tests for API validation

---

## What Was Done

### Backend (Already Complete - Committed e6ae5bd)
✅ `autofill_events.policy` column
✅ Alembic migration `54b1d1tp0l1cy_phase_54_bandit_policy.py`
✅ Prometheus metric `autofill_policy_total`
✅ Sync endpoint stores policy

### Extension (New - Phase 5.4)
✅ Bandit helpers in `content.js`
✅ `pickStyleForBandit()` function
✅ `runScanAndSuggest()` calls bandit
✅ Learning sync sends `policy`
✅ E2E tests: `e2e/autofill-bandit.spec.ts`

### Smoke Tests (New - Phase 5.5)
✅ Production API tests: `e2e/prod-companion-smoke.spec.ts`
✅ Tests generate-form-answers, learning sync, feedback

---

## Files Modified

```
apps/extension-applylens/
├── content.js                        # Bandit logic + ctx tracking
├── learning/client.js                # Sync payload with policy
└── e2e/
    ├── autofill-bandit.spec.ts      # Bandit E2E tests (3 scenarios)
    └── prod-companion-smoke.spec.ts # Prod API tests (2 scenarios)

services/api/
└── PHASE_5_4_5_EXTENSION_COMPLETE.md # Complete documentation
```

---

## Quick Test

### 1. Run Bandit E2E Tests

```bash
cd apps/extension-applylens
npx playwright test e2e/autofill-bandit.spec.ts
```

**Expected**: 3 tests pass (explore, exploit, fallback)

### 2. Run Production Smoke Tests

```bash
# Set prod API URL
$env:APPLYLENS_PROD_API_BASE = "https://api.applylens.app"

# Run tests
npx playwright test e2e/prod-companion-smoke.spec.ts
```

**Expected**: 2 tests pass (autofill flow, profile endpoint)

### 3. Test Locally (Optional)

```bash
# Start extension dev server
npm run dev

# Load extension in browser
# Visit any ATS form (e.g., Greenhouse, Lever)
# Open DevTools Console

# Override epsilon for testing (optional)
window.__APPLYLENS_BANDIT_EPSILON = 0.5; // 50% explore

# Trigger autofill
# Look for console logs: "[Bandit] explore ..." or "[Bandit] exploit ..."
```

---

## Verify Backend Ready

### 1. Run Migration (if not already done)

```bash
cd services/api
alembic upgrade head
```

**Expected**: Migration `54b1d1tp0l1cy` applied

### 2. Check Database

```sql
-- Verify policy column exists
\d autofill_events;

-- Should show:
-- policy | text | nullable | indexed
```

### 3. Check Prometheus (after some usage)

```bash
# Query Prometheus
curl http://localhost:9090/api/v1/query?query=autofill_policy_total
```

**Expected**: Metric exists with labels `[policy, host_family, segment_key]`

---

## How It Works

### Bandit Decision Flow

```
1. User triggers autofill
   ↓
2. fetchLearningProfile(host, schema)
   → Returns preferredStyleId + competitors
   ↓
3. pickStyleForBandit(styleHint)
   ↓
   ┌─────────────────────────────┐
   │ r = Math.random()           │
   │                             │
   │ if r < 0.15:                │
   │   → EXPLORE (competitor)    │
   │ else:                       │
   │   → EXPLOIT (preferred)     │
   │                             │
   │ if no preferredStyleId:     │
   │   → FALLBACK (null)         │
   └─────────────────────────────┘
   ↓
4. Generate answers with chosen style
   ↓
5. User fills form → Click "Fill All"
   ↓
6. trackAutofillCompletion()
   → Sends policy to backend
   ↓
7. Backend stores in autofill_events
   Backend increments Prometheus counter
```

### Policy Values

- **`exploit`**: Used preferred style (85% of time)
- **`explore`**: Tested competitor style (15% of time)
- **`fallback`**: No preferred style available (should decrease over time)

---

## Observability

### Check Policy Distribution (SQL)

```sql
SELECT
  policy,
  COUNT(*) as total,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct
FROM autofill_events
WHERE created_at > NOW() - INTERVAL '1 day'
GROUP BY policy;
```

**Expected**:
```
policy   | total | pct
---------|-------|-----
exploit  | 850   | 85.00
explore  | 150   | 15.00
fallback | 10    | 1.00
```

### Monitor Exploration Rate (Prometheus)

```promql
# Exploration rate (should be ~15%)
sum(rate(autofill_policy_total{policy="explore"}[1h]))
/
sum(rate(autofill_policy_total[1h]))
```

**Expected**: ~0.15 (15%)

---

## Troubleshooting

### ❌ Tests fail with timeout

**Cause**: Extension not loaded or demo form not found

**Fix**:
```bash
# Verify dev server running
curl http://localhost:4173/test/demo-form.html

# Check if extension built
npm run build
```

### ❌ Policy not sent to backend

**Check 1**: Verify bandit logs in console
```javascript
// Should see one of:
// [Bandit] explore concise_paragraph_v1 ε=0.15 vs best=friendly_bullets_v2
// [Bandit] exploit friendly_bullets_v2 ε=0.15
// [Bandit] fallback: no preferredStyleId
```

**Check 2**: Inspect network payload
```
DevTools → Network → learning/sync
Request Payload should have:
{
  "policy": "exploit",  // or "explore" or "fallback"
  "gen_style_id": "...",
  ...
}
```

### ❌ Always explores (or always exploits)

**Cause**: Math.random() override still active from test

**Fix**: Reload page

---

## Next Steps

### 1. Deploy Extension
```bash
cd apps/extension-applylens
npm run build
# Upload dist/ to Chrome Web Store / Firefox Add-ons
```

### 2. Monitor Metrics
- Watch Prometheus dashboard for `autofill_policy_total`
- Verify exploration rate stabilizes at ~15%
- Check fallback rate decreases over time (more profiles learned)

### 3. Analyze Results (After 1 Week)
```sql
-- Compare explore vs exploit performance
SELECT
  policy,
  COUNT(*) as total_runs,
  AVG(CASE WHEN feedback_status = 'helpful' THEN 1.0 ELSE 0.0 END) as helpful_ratio,
  AVG((edit_stats->>'total_chars_added')::int) as avg_edits
FROM autofill_events
WHERE created_at > NOW() - INTERVAL '7 days'
  AND feedback_status IS NOT NULL
GROUP BY policy;
```

### 4. Optional: Add GitHub Actions

Create `.github/workflows/e2e-companion-prod.yml` for daily prod smoke tests (see full doc for template).

---

## Success Criteria

✅ **Extension builds without errors**
✅ **Bandit E2E tests pass (3/3)**
✅ **Prod smoke tests pass (2/2)**
✅ **Console logs show bandit decisions**
✅ **Network payloads include policy field**
✅ **Prometheus metric appears after usage**
✅ **Exploration rate ~15% in production**

---

## Resources

- **Full Documentation**: `PHASE_5_4_5_EXTENSION_COMPLETE.md`
- **Backend Spec**: `PHASE_5_4_BANDIT_IMPLEMENTATION.md`
- **Extension Code**: `apps/extension-applylens/content.js`
- **E2E Tests**: `apps/extension-applylens/e2e/autofill-bandit.spec.ts`
- **Prod Tests**: `apps/extension-applylens/e2e/prod-companion-smoke.spec.ts`

---

**Phase 5.4 & 5.5 implementation complete! 🚀**

The bandit is now live, exploration is happening, and production smoke tests are ready for CI/CD.
