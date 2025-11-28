# Phase 5.4 Epsilon-Greedy Bandit Implementation Guide

**Goal**: Implement epsilon-greedy bandit algorithm for intelligent exploration vs exploitation in style selection.

**Context**: Backend is complete on `thread-viewer-v1` branch:
- ✅ `autofill_events.policy` column tracks "exploit" | "explore" | "fallback"
- ✅ `/api/extension/learning/sync` accepts and stores `policy` field
- ✅ `autofill_policy_total` Prometheus metric tracks policy usage by host_family × segment_key
- ✅ Backend tests written (require Docker DB to run)

**Strategy**:
- **85% Exploit**: Use `preferred_style_id` (best performing style)
- **15% Explore**: Randomly pick from competing styles to continue learning
- **Fallback**: When no `preferred_style_id` exists, policy = "fallback"

---

## Backend Implementation Summary

### Database Schema
```python
# app/models_learning_db.py
class AutofillEvent(Base):
    # ... existing columns ...
    policy = Column(
        Text,
        nullable=True,
        index=True,
        doc="Bandit policy used when choosing gen_style_id: exploit|explore|fallback",
    )
```

### API Contract
```python
# app/models_learning.py
class AutofillLearningEvent(BaseModel):
    # ... existing fields ...
    policy: Optional[str] = Field(
        default="exploit",
        description="Bandit policy used for this autofill: exploit|explore|fallback",
    )
```

### Sync Endpoint
```python
# app/routers/extension_learning.py
for event in payload.events:
    segment_key = derive_segment_key(event.job)
    policy = event.policy or "exploit"  # Default to exploit
    host_family = get_host_family(event.host)

    db_event = AutofillEvent(
        # ... other fields ...
        policy=policy,  # Store policy decision
    )

    # Increment Prometheus metric
    autofill_policy_total.labels(
        policy=policy,
        host_family=host_family,
        segment_key=segment_key,
    ).inc()
```

### Observability
```python
# app/autofill_aggregator.py
autofill_policy_total = PrometheusCounter(
    "applylens_autofill_policy_total",
    "Bandit policy usage for autofill events",
    ["policy", "host_family", "segment_key"],
)
```

Query in Grafana:
```promql
# Policy distribution by host family
sum by (policy, host_family) (
  rate(applylens_autofill_policy_total[5m])
)

# Exploration rate
sum(rate(applylens_autofill_policy_total{policy="explore"}[5m]))
/
sum(rate(applylens_autofill_policy_total[5m]))
```

---

## Extension Implementation Tasks

### 1. Add Bandit Types

**File**: `apps/extension-applylens/src/learning/types.ts`

```typescript
export type BanditPolicy = "exploit" | "explore" | "fallback";

export interface StyleHint {
  summaryStyle?: string;
  maxLength?: number;
  tone?: string;
  preferredStyleId?: string;  // Phase 5.0: Best performing style
  styleStats?: Record<string, StyleStats>;  // Phase 5.3: Performance data
}

// Phase 5.3: Style performance stats
export interface StyleStats {
  style_id: string;
  source: "form" | "segment" | "family" | "unknown";
  segment_key?: string;
  total_runs: number;
  helpful_runs: number;
  unhelpful_runs: number;
  helpful_ratio: number;
  avg_edit_chars?: number;
  is_winner: boolean;
}

export interface AutofillLearningEvent {
  host: string;
  schemaHash: string;
  suggestedMap: Record<string, string>;
  finalMap: Record<string, string>;
  genStyleId?: string;
  editStats: EditStats;
  durationMs: number;
  validationErrors: Record<string, any>;
  status: string;
  applicationId?: string;
  job?: Record<string, any>;  // Phase 5.2
  policy?: BanditPolicy;  // Phase 5.4: Bandit policy tracking
}
```

---

### 2. Implement Bandit Selection Logic

**File**: `apps/extension-applylens/content.js`

Add constant at top of file:
```javascript
// Phase 5.4: Epsilon-greedy bandit configuration
const BANDIT_EPSILON = 0.15;  // 15% exploration rate

// Allow override via window for testing
function getBanditEpsilon() {
  return window.__APPLYLENS_BANDIT_EPSILON ?? BANDIT_EPSILON;
}
```

Add helper function:
```javascript
/**
 * Phase 5.4: Epsilon-greedy bandit for style selection
 *
 * Strategy:
 * - 85% of time: Use preferred_style_id (exploit best known style)
 * - 15% of time: Random competitor from styleStats (explore alternatives)
 * - Fallback: When no preferred_style_id exists
 *
 * @param {StyleHint} styleHint - Profile style hint with preferredStyleId and styleStats
 * @returns {{styleId: string|null, policy: "exploit"|"explore"|"fallback"}}
 */
function pickStyleForBandit(styleHint) {
  if (!styleHint || !styleHint.preferredStyleId) {
    console.log("🎲 Bandit: No preferred style → fallback");
    return { styleId: null, policy: "fallback" };
  }

  const epsilon = getBanditEpsilon();
  const preferredStyleId = styleHint.preferredStyleId;

  // Get competitor styles (exclude preferred)
  const competitors = [];
  if (styleHint.styleStats) {
    for (const [styleId, stats] of Object.entries(styleHint.styleStats)) {
      if (styleId !== preferredStyleId && !stats.is_winner) {
        competitors.push(styleId);
      }
    }
  }

  // No competitors → always exploit
  if (competitors.length === 0) {
    console.log(`🎯 Bandit: Exploit ${preferredStyleId} (no competitors)`);
    return { styleId: preferredStyleId, policy: "exploit" };
  }

  // Epsilon-greedy decision
  const roll = Math.random();

  if (roll < epsilon) {
    // EXPLORE: Pick random competitor
    const randomIndex = Math.floor(Math.random() * competitors.length);
    const exploredStyle = competitors[randomIndex];

    console.log(
      `🔍 Bandit: Explore ${exploredStyle} ` +
      `(roll=${roll.toFixed(3)} < ε=${epsilon}, ` +
      `${competitors.length} competitors)`
    );

    return { styleId: exploredStyle, policy: "explore" };
  } else {
    // EXPLOIT: Use preferred style
    console.log(
      `🎯 Bandit: Exploit ${preferredStyleId} ` +
      `(roll=${roll.toFixed(3)} ≥ ε=${epsilon})`
    );

    return { styleId: preferredStyleId, policy: "exploit" };
  }
}
```

---

### 3. Integrate Bandit in Autofill Flow

**File**: `apps/extension-applylens/content.js`

**Locate** the autofill generation code (in `runScanAndSuggest` or similar):

```javascript
// BEFORE Phase 5.4:
const profile = await fetchLearningProfile(host, schemaHash);
const baseStyleHint = profile?.styleHint || null;

let effectiveStyleHint = baseStyleHint;
if (baseStyleHint && baseStyleHint.preferredStyleId) {
  effectiveStyleHint = {
    ...baseStyleHint,
    style_id: baseStyleHint.preferredStyleId,
  };
}

const data = await fetchFormAnswers(ctx.job, fields, effectiveStyleHint);
```

**AFTER Phase 5.4** (with bandit):

```javascript
const profile = await fetchLearningProfile(host, schemaHash);
const baseStyleHint = profile?.styleHint || null;

// Phase 5.4: Epsilon-greedy bandit for style selection
const { styleId, policy } = pickStyleForBandit(baseStyleHint);

// Store policy in context for learning sync
ctx.banditPolicy = policy;

let effectiveStyleHint = null;
if (styleId) {
  // Backend expects snake_case style_id
  effectiveStyleHint = {
    ...baseStyleHint,
    style_id: styleId,
  };

  console.log(
    `📊 Using style: ${styleId} (policy=${policy})`
  );
} else {
  // Fallback: no preferred style, use base hint
  effectiveStyleHint = baseStyleHint;
}

const data = await fetchFormAnswers(ctx.job, fields, effectiveStyleHint);

// Store the actual gen_style_id used (for learning event)
ctx.genStyleId = styleId || data.gen_style_id || null;
```

---

### 4. Include Policy in Learning Sync

**File**: `apps/extension-applylens/content.js`

**Locate** learning event creation (usually in sync function):

```javascript
// BEFORE Phase 5.4:
const event = {
  host: ctx.host,
  schema_hash: ctx.schemaHash,
  suggested_map: ctx.suggestedMap,
  final_map: ctx.finalMap,
  gen_style_id: ctx.genStyleId,
  edit_stats: ctx.editStats,
  duration_ms: ctx.durationMs,
  validation_errors: ctx.validationErrors,
  status: ctx.status,
  application_id: ctx.applicationId,
  job: ctx.job,  // Phase 5.2
};
```

**AFTER Phase 5.4**:

```javascript
const event = {
  host: ctx.host,
  schema_hash: ctx.schemaHash,
  suggested_map: ctx.suggestedMap,
  final_map: ctx.finalMap,
  gen_style_id: ctx.genStyleId,
  edit_stats: ctx.editStats,
  duration_ms: ctx.durationMs,
  validation_errors: ctx.validationErrors,
  status: ctx.status,
  application_id: ctx.applicationId,
  job: ctx.job,  // Phase 5.2
  policy: ctx.banditPolicy || "exploit",  // Phase 5.4: Default to exploit
};
```

---

### 5. Add E2E Tests for Bandit

**File**: `apps/extension-applylens/e2e/autofill-bandit.spec.ts`

```typescript
/**
 * Phase 5.4: Epsilon-greedy bandit E2E tests
 *
 * @tags @companion @bandit
 *
 * Validates:
 * - Exploration: Random competitor picked when roll < epsilon
 * - Exploitation: Preferred style used when roll >= epsilon
 * - Policy tracking: Learning sync includes policy field
 * - Fallback: No preferred style → policy="fallback"
 */

import { test, expect } from "@playwright/test";
import { loadContentPatched } from "./utils/contentPatcher";

test.describe("@companion @bandit", () => {
  test("explores competitor style when Math.random < epsilon", async ({ page }) => {
    // 1) Mock profile with preferred style + competitors
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "greenhouse.io",
          schema_hash: "bandit-test",
          canonical_map: {
            "input[name='name']": "full_name",
            "textarea[name='cover']": "cover_letter",
          },
          style_hint: {
            preferred_style_id: "friendly_bullets_v1",
            summary_style: "bullets",
            style_stats: {
              friendly_bullets_v1: {
                style_id: "friendly_bullets_v1",
                source: "form",
                total_runs: 20,
                helpful_runs: 16,
                unhelpful_runs: 4,
                helpful_ratio: 0.8,
                is_winner: true,
              },
              professional_narrative_v1: {
                style_id: "professional_narrative_v1",
                source: "segment",
                total_runs: 15,
                helpful_runs: 9,
                unhelpful_runs: 6,
                helpful_ratio: 0.6,
                is_winner: false,
              },
              concise_achievements_v1: {
                style_id: "concise_achievements_v1",
                source: "family",
                total_runs: 10,
                helpful_runs: 5,
                unhelpful_runs: 5,
                helpful_ratio: 0.5,
                is_winner: false,
              },
            },
          },
        }),
      });
    });

    // 2) Force exploration by overriding Math.random
    await page.addInitScript(() => {
      // Force roll < epsilon (0.15) to trigger exploration
      Math.random = () => 0.01;
      // @ts-ignore
      window.__APPLYLENS_BANDIT_EPSILON = 0.15;
    });

    let capturedGenerateRequest: any = null;
    let capturedSyncRequest: any = null;

    // 3) Capture generate-form-answers request
    await page.route("**/api/extension/generate-form-answers**", async (route) => {
      capturedGenerateRequest = await route.request().postDataJSON();

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answers: [
            { field_id: "name", answer: "Test User" },
            { field_id: "cover", answer: "Explored style cover letter" },
          ],
          gen_style_id: capturedGenerateRequest.style_hint?.style_id || null,
        }),
      });
    });

    // 4) Capture learning sync request
    await page.route("**/api/extension/learning/sync**", async (route) => {
      capturedSyncRequest = await route.request().postDataJSON();

      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({ status: "accepted", persisted: true }),
      });
    });

    // 5) Load content script and trigger autofill
    await loadContentPatched(page);
    await page.goto("/test/demo-form.html");

    await page.evaluate(() => {
      // @ts-ignore
      window.__APPLYLENS_HOST_OVERRIDE__ = "greenhouse.io";
    });

    const scanButton = page.locator("#al_scan_button");
    await scanButton.click();

    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible({ timeout: 5000 });

    const fillAllButton = panel.getByTestId("al-fill-all");
    await fillAllButton.click();

    await page.waitForTimeout(1500);

    // 6) Assert: Competitor style was chosen (exploration)
    expect(capturedGenerateRequest).not.toBeNull();
    const requestedStyleId = capturedGenerateRequest.style_hint?.style_id;

    // Should NOT be the preferred style
    expect(requestedStyleId).not.toBe("friendly_bullets_v1");

    // Should be one of the competitors
    const competitors = ["professional_narrative_v1", "concise_achievements_v1"];
    expect(competitors).toContain(requestedStyleId);

    // 7) Assert: Learning sync has policy="explore"
    expect(capturedSyncRequest).not.toBeNull();
    expect(capturedSyncRequest.events).toBeDefined();
    expect(capturedSyncRequest.events.length).toBeGreaterThan(0);

    const event = capturedSyncRequest.events[0];
    expect(event.policy).toBe("explore");
    expect(event.gen_style_id).toBe(requestedStyleId);

    console.log("✅ Exploration test passed: competitor style chosen, policy=explore");
  });

  test("exploits preferred style when Math.random >= epsilon", async ({ page }) => {
    // 1) Same profile with preferred + competitors
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "greenhouse.io",
          schema_hash: "bandit-test",
          canonical_map: { "input[name='name']": "full_name" },
          style_hint: {
            preferred_style_id: "friendly_bullets_v1",
            style_stats: {
              friendly_bullets_v1: {
                style_id: "friendly_bullets_v1",
                helpful_ratio: 0.8,
                is_winner: true,
              },
              professional_narrative_v1: {
                style_id: "professional_narrative_v1",
                helpful_ratio: 0.6,
                is_winner: false,
              },
            },
          },
        }),
      });
    });

    // 2) Force exploitation by overriding Math.random
    await page.addInitScript(() => {
      // Force roll >= epsilon to trigger exploitation
      Math.random = () => 0.99;
      // @ts-ignore
      window.__APPLYLENS_BANDIT_EPSILON = 0.15;
    });

    let capturedGenerateRequest: any = null;
    let capturedSyncRequest: any = null;

    await page.route("**/api/extension/generate-form-answers**", async (route) => {
      capturedGenerateRequest = await route.request().postDataJSON();

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answers: [{ field_id: "name", answer: "Test User" }],
          gen_style_id: capturedGenerateRequest.style_hint?.style_id,
        }),
      });
    });

    await page.route("**/api/extension/learning/sync**", async (route) => {
      capturedSyncRequest = await route.request().postDataJSON();

      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({ status: "accepted", persisted: true }),
      });
    });

    // 3) Trigger autofill
    await loadContentPatched(page);
    await page.goto("/test/demo-form.html");

    await page.evaluate(() => {
      // @ts-ignore
      window.__APPLYLENS_HOST_OVERRIDE__ = "greenhouse.io";
    });

    const scanButton = page.locator("#al_scan_button");
    await scanButton.click();

    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible();

    const fillAllButton = panel.getByTestId("al-fill-all");
    await fillAllButton.click();

    await page.waitForTimeout(1500);

    // 4) Assert: Preferred style was chosen (exploitation)
    expect(capturedGenerateRequest).not.toBeNull();
    const requestedStyleId = capturedGenerateRequest.style_hint?.style_id;

    // Should be the preferred style
    expect(requestedStyleId).toBe("friendly_bullets_v1");

    // 5) Assert: Learning sync has policy="exploit"
    expect(capturedSyncRequest).not.toBeNull();
    const event = capturedSyncRequest.events[0];
    expect(event.policy).toBe("exploit");
    expect(event.gen_style_id).toBe("friendly_bullets_v1");

    console.log("✅ Exploitation test passed: preferred style chosen, policy=exploit");
  });

  test("fallback when no preferred_style_id", async ({ page }) => {
    // 1) Mock profile WITHOUT preferred_style_id
    await page.route("**/api/extension/learning/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          host: "new-ats.com",
          schema_hash: "new-schema",
          canonical_map: { "input[name='email']": "email" },
          style_hint: {
            summary_style: "narrative",
            max_length: 1000,
            // No preferred_style_id
          },
        }),
      });
    });

    let capturedSyncRequest: any = null;

    await page.route("**/api/extension/generate-form-answers**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answers: [{ field_id: "email", answer: "user@example.com" }],
        }),
      });
    });

    await page.route("**/api/extension/learning/sync**", async (route) => {
      capturedSyncRequest = await route.request().postDataJSON();

      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({ status: "accepted", persisted: true }),
      });
    });

    // 2) Trigger autofill
    await loadContentPatched(page);
    await page.goto("/test/demo-form.html");

    await page.evaluate(() => {
      // @ts-ignore
      window.__APPLYLENS_HOST_OVERRIDE__ = "new-ats.com";
    });

    const scanButton = page.locator("#al_scan_button");
    await scanButton.click();

    const panel = page.locator('[data-testid="al-panel"]');
    await expect(panel).toBeVisible();

    const fillAllButton = panel.getByTestId("al-fill-all");
    await fillAllButton.click();

    await page.waitForTimeout(1500);

    // 3) Assert: Learning sync has policy="fallback"
    expect(capturedSyncRequest).not.toBeNull();
    const event = capturedSyncRequest.events[0];
    expect(event.policy).toBe("fallback");

    console.log("✅ Fallback test passed: no preferred style → policy=fallback");
  });
});
```

**Add to package.json**:
```json
{
  "scripts": {
    "e2e:bandit": "playwright test --grep='@bandit'"
  }
}
```

**Run tests**:
```bash
npm run e2e:bandit
```

---

## 6. Validation Checklist

### Phase 5.4 Complete When:

#### Backend (✅ Complete)
- [x] `autofill_events.policy` column exists with index
- [x] Alembic migration `54b1d1tp0l1cy_phase_54_bandit_policy.py`
- [x] `AutofillLearningEvent.policy` Pydantic field
- [x] `/api/extension/learning/sync` stores policy
- [x] `autofill_policy_total` Prometheus counter incremented
- [x] Tests in `tests/test_learning_bandit_policy.py` (require Docker DB)

#### Extension (⏳ Pending)
- [ ] `BanditPolicy` type in `src/learning/types.ts`
- [ ] `BANDIT_EPSILON` constant in `content.js`
- [ ] `pickStyleForBandit()` function implements ε-greedy
- [ ] Bandit integrated in autofill flow
- [ ] `ctx.banditPolicy` tracked and sent to sync
- [ ] E2E tests in `e2e/autofill-bandit.spec.ts`
- [ ] Test 1: Exploration (Math.random < ε) → competitor + policy="explore"
- [ ] Test 2: Exploitation (Math.random ≥ ε) → preferred + policy="exploit"
- [ ] Test 3: Fallback (no preferred) → policy="fallback"
- [ ] All 3 tests pass: `npm run e2e:bandit`

#### Integration Verified
- [ ] All existing `@companion` tests still pass
- [ ] No regressions in Phase 5.3 explainability
- [ ] No regressions in Phase 5.0 style tuning
- [ ] Metrics visible in Grafana dashboard

---

## 7. Observability & Analytics

### Grafana Queries

**Exploration rate by host family**:
```promql
sum by (host_family) (
  rate(applylens_autofill_policy_total{policy="explore"}[1h])
)
/
sum by (host_family) (
  rate(applylens_autofill_policy_total[1h])
)
```

**Policy distribution**:
```promql
sum by (policy) (
  rate(applylens_autofill_policy_total[5m])
)
```

**Segment-level exploration**:
```promql
sum by (segment_key, policy) (
  rate(applylens_autofill_policy_total[15m])
)
```

### Expected Metrics
- **Exploration rate**: ~15% of autofills should have policy="explore"
- **Exploitation rate**: ~85% should have policy="exploit"
- **Fallback rate**: Low (only for new forms without data)

### Database Queries

**Check policy distribution**:
```sql
SELECT
  policy,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM autofill_events
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY policy
ORDER BY count DESC;
```

**Exploration success rate**:
```sql
-- Compare helpful_ratio for explore vs exploit
SELECT
  policy,
  COUNT(*) as total,
  SUM(CASE WHEN feedback_status = 'helpful' THEN 1 ELSE 0 END) as helpful,
  ROUND(
    SUM(CASE WHEN feedback_status = 'helpful' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
    2
  ) as helpful_percentage
FROM autofill_events
WHERE policy IN ('explore', 'exploit')
  AND feedback_status IN ('helpful', 'unhelpful')
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY policy;
```

---

## 8. Testing Strategy

### Unit Tests (TypeScript)
- `pickStyleForBandit()` returns correct policy
- Epsilon threshold logic (< vs ≥)
- Fallback when no preferredStyleId
- Competitor selection randomness

### E2E Tests (Playwright)
- Force exploration via Math.random override
- Force exploitation via Math.random override
- Verify policy in learning sync payload
- Check style_id matches bandit decision

### Manual Testing
1. **Enable verbose logging**:
   ```javascript
   localStorage.setItem("APPLYLENS_DEBUG_BANDIT", "true");
   ```

2. **Check console logs**:
   - "🎲 Bandit: No preferred style → fallback"
   - "🔍 Bandit: Explore [style] (roll=0.05 < ε=0.15)"
   - "🎯 Bandit: Exploit [style] (roll=0.85 ≥ ε=0.15)"

3. **Verify in DevTools Network**:
   - Check `/sync` request body has `policy` field
   - Check `/generate-form-answers` has correct `style_id`

4. **Check Grafana dashboard**:
   - Exploration rate near 15%
   - Policy metrics incrementing

---

## 9. Rollout Plan

### Phase 1: Canary (10% of users)
- Deploy extension with bandit enabled
- Monitor exploration rate (should be ~15%)
- Monitor fallback rate (should be low)
- Check for errors/crashes

### Phase 2: Gradual Rollout (50% → 100%)
- Increase rollout percentage
- Monitor helpful_ratio for explore vs exploit
- Adjust epsilon if needed (via feature flag)

### Phase 3: Analysis & Tuning
- Compare helpful_ratio: explore vs exploit
- Identify segments where exploration helps
- Consider dynamic epsilon per host_family

---

## 10. Future Enhancements

### Dynamic Epsilon
```javascript
// Adjust exploration rate based on data quality
function getDynamicEpsilon(styleStats) {
  const totalRuns = Object.values(styleStats).reduce(
    (sum, s) => sum + s.total_runs,
    0
  );

  if (totalRuns < 10) return 0.30;  // High exploration for new forms
  if (totalRuns < 50) return 0.20;  // Medium exploration
  return 0.15;  // Standard exploration
}
```

### Thompson Sampling
- Sample from Beta distribution instead of ε-greedy
- More sophisticated exploration strategy
- Better exploitation of uncertainty

### Contextual Bandits
- Consider job type, segment_key, time of day
- Personalized epsilon per context
- Multi-armed contextual bandit

---

## Summary

Phase 5.4 adds intelligent exploration via epsilon-greedy bandit:

✅ **Backend Complete**:
- Database schema tracks policy decisions
- Sync endpoint stores policy + increments metrics
- Prometheus observability ready
- Tests written (require Docker DB)

⏳ **Extension Pending**:
- `pickStyleForBandit()` implements ε-greedy selection
- 85% exploit preferred style, 15% explore competitors
- Policy tracked in learning events
- E2E tests verify explore/exploit/fallback paths

**The bandit ensures continuous learning while optimizing for user satisfaction!** 🎰📊
