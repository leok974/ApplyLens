# Phase 5.4.5: Bandit Kill Switch Implementation

## Overview
Added global kill switch for epsilon-greedy bandit exploration to allow emergency rollback or user preference control.

## Implementation Complete ✅

### Backend Changes (via user)
**File:** `services/api/app/config.py`
- Added `COMPANION_BANDIT_ENABLED: bool = True` environment variable
- Default: `True` (bandit active)
- Set `APPLYLENS_COMPANION_BANDIT_ENABLED=false` to disable globally

**File:** `services/api/app/routers/extension_learning.py`
- Updated `/sync` endpoint: Forces `policy="fallback"` when bandit disabled
- Updated `/profile` endpoint: Returns `preferred_style_id=None` when bandit disabled
- Behavior: All learning events logged with `policy="fallback"` when disabled

### Extension Changes (completed)
**File:** `apps/extension-applylens/content.js`

**1. Added `isBanditEnabled()` helper function (lines 115-127):**
```javascript
/**
 * Check if bandit exploration is enabled.
 * Reads from window.__APPLYLENS_BANDIT_ENABLED (set by settings or test).
 * Defaults to true if not explicitly set to false.
 */
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

**2. Updated `runScanAndSuggest()` to use kill switch (lines 415-434):**
```javascript
// Phase 5.4 — epsilon-greedy bandit
const styleHint = profile?.styleHint || null;

let chosenStyleId = null;
let banditPolicy = "fallback";

if (isBanditEnabled() && styleHint && styleHint.preferredStyleId) {
  // Bandit is enabled - use normal exploration logic
  const banditResult = pickStyleForBandit(styleHint);
  chosenStyleId = banditResult.styleId;
  banditPolicy = banditResult.policy;
} else {
  // Bandit disabled globally or no style hint available - fallback
  chosenStyleId = styleHint ? styleHint.preferredStyleId : null;
  banditPolicy = "fallback";
  if (!isBanditEnabled()) {
    console.log("[Bandit] DISABLED via kill switch - using fallback policy");
  }
}
```

**Key Changes:**
- Checks `isBanditEnabled()` before calling `pickStyleForBandit()`
- When disabled: Forces `policy="fallback"`, still uses `preferredStyleId` if available
- Logs clear message when kill switch is active
- Maintains existing `pickStyleForBandit()` logic intact

## How to Use

### Backend Kill Switch
```bash
# Disable bandit globally (affects all users)
export APPLYLENS_COMPANION_BANDIT_ENABLED=false

# Or in .env file
APPLYLENS_COMPANION_BANDIT_ENABLED=false

# Restart API
uvicorn app.main:app --reload
```

**Effect:**
- Backend stops sending `preferred_style_id` in `/profile` responses
- All learning events logged with `policy="fallback"`
- Metrics show bandit is disabled

### Extension Kill Switch
```javascript
// In browser console or settings page
window.__APPLYLENS_BANDIT_ENABLED = false;
```

**Effect:**
- Extension stops calling `pickStyleForBandit()`
- Always uses `policy="fallback"`
- Still uses `preferredStyleId` from profile if backend provides it

### Combined (Recommended for Emergency Rollback)
```bash
# 1. Backend: Disable globally
export APPLYLENS_COMPANION_BANDIT_ENABLED=false

# 2. Extension: Users can also disable locally
window.__APPLYLENS_BANDIT_ENABLED = false;
```

## Testing

### Manual Testing

**1. Test Backend Kill Switch:**
```bash
# Terminal 1: Start API with bandit disabled
cd d:\ApplyLens\services\api
export APPLYLENS_COMPANION_BANDIT_ENABLED=false
uvicorn app.main:app --reload --port 8888

# Terminal 2: Check profile endpoint
curl http://localhost:8888/api/extension/learning/profile?host=test&schema_hash=test

# Expected: preferred_style_id should be null
# Expected: style_stats should be empty or minimal
```

**2. Test Extension Kill Switch:**
```javascript
// Open browser console on a job form
window.__APPLYLENS_BANDIT_ENABLED = false;

// Trigger autofill (click ApplyLens panel)
// Check console output

// Expected log: "[Bandit] DISABLED via kill switch - using fallback policy"
// Expected: No "[Bandit] explore" or "[Bandit] exploit" logs

// Check learning sync event
// Expected: policy="fallback"
```

**3. Test Re-Enable:**
```javascript
// Re-enable bandit
window.__APPLYLENS_BANDIT_ENABLED = true;

// Trigger autofill again
// Expected: Normal bandit behavior resumes
// Expected logs: "[Bandit] exploit" or "[Bandit] explore"
```

### Automated Testing

**Test file to add:** `e2e/autofill-bandit-killswitch.spec.ts`

```typescript
import { test, expect } from "@playwright/test";

test.describe("@companion @bandit @killswitch", () => {
  test("uses fallback policy when bandit is globally disabled", async ({ page }) => {
    let lastSyncBody: any = null;

    // Mock profile with preferred_style_id
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "test-ats.com",
          schema_hash: "test-schema",
          canonical_map: {},
          style_hint: {
            preferred_style_id: "friendly_bullets_v1",
            style_stats: {
              chosen: {
                style_id: "friendly_bullets_v1",
                helpful_ratio: 0.8,
                total_runs: 20,
              },
              competitors: [
                {
                  style_id: "concise_paragraph_v1",
                  helpful_ratio: 0.7,
                  total_runs: 10,
                },
              ],
            },
          },
        }),
      });
    });

    // Mock generate answers
    await page.route("**/api/extension/generate-form-answers**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answers: [
            { field_id: "full_name", answer: "Test User" },
            { field_id: "summary", answer: "Test answer" },
          ],
        }),
      });
    });

    // Capture sync request
    await page.route("**/api/extension/learning/sync**", async (route) => {
      const request = route.request();
      lastSyncBody = await request.postDataJSON();
      await route.fulfill({ status: 200, body: "{}" });
    });

    // Navigate to demo form
    await page.goto("http://127.0.0.1:5177/demo-form.html");

    // DISABLE BANDIT via global flag
    await page.evaluate(() => {
      (window as any).__APPLYLENS_BANDIT_ENABLED = false;
    });

    // Inject content script and trigger autofill
    // (Add loadContentPatched() pattern here - see other companion tests)

    // Wait for sync
    await page.waitForTimeout(1000);

    // Assertions
    expect(lastSyncBody).not.toBeNull();
    expect(lastSyncBody.policy).toBe("fallback");

    // Style should still be used if available
    expect(lastSyncBody.gen_style_id).toBe("friendly_bullets_v1");
  });

  test("resumes normal bandit behavior when re-enabled", async ({ page }) => {
    // Similar test but with __APPLYLENS_BANDIT_ENABLED = true
    // Should see policy="exploit" or policy="explore" depending on Math.random()
  });
});
```

### Monitoring

**Prometheus Metrics to Watch:**
```promql
# When kill switch is active, should see 100% fallback policy
sum by (policy) (rate(autofill_policy_total[5m]))

# Expected when DISABLED:
# policy="fallback" = 100%
# policy="explore" = 0%
# policy="exploit" = 0%

# Expected when ENABLED (normal):
# policy="exploit" ≈ 85-90%
# policy="explore" ≈ 10-15%
# policy="fallback" < 5%
```

**Database Query:**
```sql
-- Check policy distribution in last hour
SELECT
  policy,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentage
FROM autofill_events
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY policy;

-- When kill switch is active, should see:
-- policy | count | percentage
-- --------+-------+-----------
-- fallback| 1234  | 100.00
```

## Use Cases

### 1. Emergency Rollback
**Scenario:** Bandit exploration is causing issues (e.g., poor quality variations)

**Action:**
```bash
# Backend: Disable globally for all users
export APPLYLENS_COMPANION_BANDIT_ENABLED=false
# Restart API

# Monitor metrics
# Expected: All new requests show policy="fallback"
```

### 2. User Preference
**Scenario:** Power user wants consistent results, no experimentation

**Implementation:** Add toggle in extension settings page
```javascript
// settings.js
chrome.storage.sync.set({ banditEnabled: false });

// content.js - read from storage
const { banditEnabled } = await chrome.storage.sync.get('banditEnabled');
if (typeof banditEnabled === 'boolean') {
  window.__APPLYLENS_BANDIT_ENABLED = banditEnabled;
}
```

### 3. A/B Testing
**Scenario:** Test impact of bandit exploration on user satisfaction

**Implementation:**
```javascript
// Randomly assign users to control/treatment groups
const userId = getUserId();
const isControl = hashUserId(userId) % 2 === 0;

window.__APPLYLENS_BANDIT_ENABLED = !isControl;

// Control: No exploration (always fallback)
// Treatment: Normal bandit behavior (10% explore)
```

### 4. Gradual Rollout
**Scenario:** Enable bandit for 10% of users initially

**Backend:**
```python
# In extension_learning.py
user_hash = hashlib.md5(user_id.encode()).hexdigest()
enable_bandit = int(user_hash, 16) % 100 < 10  # 10% of users

if not enable_bandit:
    style_hint.preferred_style_id = None
```

## Observability

### Logs to Monitor

**Extension Console (when disabled):**
```
[Bandit] DISABLED via kill switch - using fallback policy
[Learning] Syncing event with policy=fallback
```

**Extension Console (when enabled - normal):**
```
[Bandit] exploit friendly_bullets_v1 ε=0.15
[Learning] Syncing event with policy=exploit
```

**Backend Logs:**
```
# When COMPANION_BANDIT_ENABLED=false
INFO: Profile request: Bandit disabled globally, not sending preferred_style_id
INFO: Learning sync: Forcing policy=fallback (bandit disabled)
```

### Alerts to Configure

**Grafana Alert: Unexpected Fallback Rate**
```promql
# Alert if fallback rate unexpectedly high (suggests kill switch active or bug)
sum(rate(autofill_policy_total{policy="fallback"}[5m]))
/
sum(rate(autofill_policy_total[5m]))
> 0.20  # Alert if >20% fallback

# Notification: "ApplyLens bandit fallback rate elevated. Check if kill switch is active."
```

**Sentry Alert: Kill Switch Activation**
```javascript
// In content.js
if (!isBanditEnabled()) {
  Sentry.captureMessage("Bandit kill switch active", {
    level: "info",
    tags: { feature: "bandit", status: "disabled" }
  });
}
```

## Rollback Plan

**If kill switch causes issues:**

1. **Extension:** Remove kill switch check (2-line change)
   ```javascript
   // Revert to always calling pickStyleForBandit
   const { styleId, policy } = pickStyleForBandit(styleHint);
   ```

2. **Backend:** Ignore `COMPANION_BANDIT_ENABLED` flag
   ```python
   # Remove all references to agent_settings.COMPANION_BANDIT_ENABLED
   # Always send preferred_style_id
   ```

3. **Deploy:** Push hotfix to production
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

## Summary

✅ **Backend Kill Switch:** `COMPANION_BANDIT_ENABLED` environment variable
✅ **Extension Kill Switch:** `window.__APPLYLENS_BANDIT_ENABLED` global flag
✅ **Graceful Degradation:** Uses fallback policy, still works without exploration
✅ **Observability:** Metrics and logs clearly show when disabled
✅ **User Control:** Can be toggled via settings (future enhancement)
✅ **Production Safety:** Easy emergency rollback if bandit causes issues

**Next Steps:**
1. Add kill switch toggle to extension settings UI
2. Add automated E2E test for kill switch
3. Monitor metrics for 24-48 hours after deployment
4. Document kill switch in user-facing docs

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
