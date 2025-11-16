# Phase 5.4.5 Kill Switch Implementation - Summary

**Date**: November 15, 2025
**Status**: ✅ **COMPLETE**
**Scope**: Backend + Extension

---

## What Was Implemented

### Global Kill Switch for Epsilon-Greedy Bandit

**Purpose:** Allow emergency rollback or user preference control for bandit exploration

**Behavior When Disabled:**
- No style exploration (no random competitor testing)
- All autofills use `policy="fallback"`
- Still uses `preferredStyleId` from backend if available
- All metrics show `policy="fallback"` distribution

---

## Changes Made

### ✅ Backend (Completed by User)

**File:** `services/api/app/config.py`
```python
# Added environment variable
COMPANION_BANDIT_ENABLED: bool = True  # Global kill-switch
```

**File:** `services/api/app/routers/extension_learning.py`
```python
# Import added
from app.config import agent_settings

# In /sync endpoint: Force fallback policy when disabled
if not agent_settings.COMPANION_BANDIT_ENABLED:
    policy = "fallback"

# In /profile endpoint: Don't send style recommendations when disabled
if not agent_settings.COMPANION_BANDIT_ENABLED:
    preferred_style_id = None
```

### ✅ Extension (Completed)

**File:** `apps/extension-applylens/content.js`

**1. Added Kill Switch Helper (lines 115-127):**
```javascript
function isBanditEnabled() {
  try {
    if (
      typeof window !== "undefined" &&
      typeof window.__APPLYLENS_BANDIT_ENABLED === "boolean"
    ) {
      return window.__APPLYLENS_BANDIT_ENABLED;
    }
  } catch (e) {
    // ignore
  }
  return true; // Default: bandit enabled
}
```

**2. Updated Bandit Logic (lines 415-434):**
```javascript
const styleHint = profile?.styleHint || null;

let chosenStyleId = null;
let banditPolicy = "fallback";

if (isBanditEnabled() && styleHint && styleHint.preferredStyleId) {
  // Bandit enabled - normal exploration
  const banditResult = pickStyleForBandit(styleHint);
  chosenStyleId = banditResult.styleId;
  banditPolicy = banditResult.policy;
} else {
  // Bandit disabled - fallback
  chosenStyleId = styleHint ? styleHint.preferredStyleId : null;
  banditPolicy = "fallback";
  if (!isBanditEnabled()) {
    console.log("[Bandit] DISABLED via kill switch - using fallback policy");
  }
}
```

---

## How to Use

### Backend: Disable Globally
```bash
# Set environment variable
export APPLYLENS_COMPANION_BANDIT_ENABLED=false

# Or in .env file
APPLYLENS_COMPANION_BANDIT_ENABLED=false

# Restart API
uvicorn app.main:app --reload
```

**Effect:** Backend stops sending style recommendations to all users

### Extension: Disable Locally
```javascript
// In browser console or settings page
window.__APPLYLENS_BANDIT_ENABLED = false;
```

**Effect:** Extension stops exploring, always uses fallback policy

### Recommended: Combined Approach
```bash
# 1. Backend: Global disable
export APPLYLENS_COMPANION_BANDIT_ENABLED=false

# 2. Extension: Local disable (for individual users)
window.__APPLYLENS_BANDIT_ENABLED = false;
```

---

## Testing

### Manual Testing

**1. Test Extension Kill Switch:**
```javascript
// Open browser console on a job form
window.__APPLYLENS_BANDIT_ENABLED = false;

// Trigger autofill
// Expected console log: "[Bandit] DISABLED via kill switch - using fallback policy"
// Expected: policy="fallback" in learning sync
```

**2. Test Backend Kill Switch:**
```bash
# Terminal: Start API with bandit disabled
export APPLYLENS_COMPANION_BANDIT_ENABLED=false
uvicorn app.main:app --reload --port 8888

# Check profile endpoint
curl http://localhost:8888/api/extension/learning/profile?host=test&schema_hash=test

# Expected: preferred_style_id should be null
```

**3. Test Re-Enable:**
```javascript
// Re-enable
window.__APPLYLENS_BANDIT_ENABLED = true;

// Trigger autofill
// Expected: Normal bandit behavior (explore/exploit logs)
```

### Automated Testing

**Create test file:** `e2e/autofill-bandit-killswitch.spec.ts`

```typescript
test("uses fallback policy when bandit is globally disabled", async ({ page }) => {
  // Disable bandit
  await page.evaluate(() => {
    (window as any).__APPLYLENS_BANDIT_ENABLED = false;
  });

  // Trigger autofill
  // ...

  // Assert: policy="fallback"
  expect(lastSyncBody.policy).toBe("fallback");
});
```

**Note:** Full E2E test example in `PHASE_5_4_5_KILLSWITCH_GUIDE.md`

---

## Monitoring

### Metrics to Watch

**When Disabled (Expected):**
```promql
# All requests should be fallback
sum by (policy) (rate(autofill_policy_total[5m]))

# Expected distribution:
# policy="fallback" = 100%
# policy="explore" = 0%
# policy="exploit" = 0%
```

**When Enabled (Normal):**
```promql
# Expected distribution:
# policy="exploit" ≈ 85-90%
# policy="explore" ≈ 10-15%
# policy="fallback" < 5%
```

### Database Query

```sql
SELECT
  policy,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentage
FROM autofill_events
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY policy;
```

**When kill switch active:**
- `policy="fallback"` should be 100%

---

## Use Cases

### 1. Emergency Rollback
**Scenario:** Bandit exploration causing quality issues

**Action:**
```bash
# Disable globally
export APPLYLENS_COMPANION_BANDIT_ENABLED=false
# Restart API
```

### 2. User Preference
**Scenario:** Power user wants consistent results

**Implementation:** Add toggle in extension settings
```javascript
chrome.storage.sync.set({ banditEnabled: false });
```

### 3. Gradual Rollout
**Scenario:** Enable for 10% of users initially

**Backend logic:**
```python
user_hash = hashlib.md5(user_id.encode()).hexdigest()
enable_bandit = int(user_hash, 16) % 100 < 10  # 10% rollout
```

---

## Documentation

**Complete Implementation Guide:** `PHASE_5_4_5_KILLSWITCH_GUIDE.md`

Includes:
- Detailed implementation notes
- Testing procedures
- Monitoring setup
- Use case examples
- Rollback plan
- Observability configuration

---

## Summary

✅ **Backend:** `COMPANION_BANDIT_ENABLED` environment variable
✅ **Extension:** `window.__APPLYLENS_BANDIT_ENABLED` global flag
✅ **Graceful Degradation:** Works without exploration
✅ **Logging:** Clear console messages when disabled
✅ **Metrics:** Policy distribution reflects kill switch state
✅ **Production Ready:** Easy emergency rollback

**Next Steps:**
1. ✅ Implementation complete
2. ⏳ Add kill switch toggle to settings UI (future enhancement)
3. ⏳ Deploy and monitor metrics
4. ⏳ Document in user-facing help docs

**Status:** Ready for production deployment 🎉

---

## Future Enhancements

- **Add kill switch toggle to extension settings UI**
  Expose the bandit kill switch as a user-facing toggle in the ApplyLens Companion settings page, wired to `window.__APPLYLENS_BANDIT_ENABLED` and persisted via localStorage.

- **Add automated E2E test (optional – template provided)**
  Promote the kill-switch scenario from the guide into a proper Playwright test that verifies `policy="fallback"` when the switch is disabled, alongside the existing bandit explore/exploit tests.

- **Set up Grafana alert for unexpected fallback rate**
  Add a Prometheus alert that fires when `autofill_policy_total{policy="fallback"}` exceeds a safe percentage of total bandit events over a rolling window (e.g. >20% for 30 minutes), indicating bandit is degraded or stuck in fallback.

- **Document in user-facing help docs**
  Add a short "Experimental styles & safety controls" section to the ApplyLens help docs, explaining what experimental styles are, how the kill switch works, and how users can opt out.
