# Phase 6: Bandit Feature Flag & Rollout Controls

**Status**: Implementation Guide
**Created**: 2025-11-15
**Goal**: Safe enable/disable of bandit behavior globally and per-user, while preserving event logging

---

## Overview

Phase 6 adds feature flag controls to safely rollout the bandit learning system introduced in Phase 5. The flag allows disabling bandit-based style selection while continuing to log autofill events for future analysis.

**Key Principle**: When disabled, system behaves **exactly** like Phase 5 pre-bandit fallback (uses `preferredStyleId` from aggregated statistics).

---

## Backend Implementation

### 1. Add Feature Flag to AgentSettings

**File**: `services/api/app/config.py`

Add to `AgentSettings` class after existing Phase 5 flags:

```python
# Phase 6: Rollout & Guardrails (Companion Learning / Bandit)
COMPANION_BANDIT_ENABLED: bool = True  # Enable bandit-based style selection
```

**Pattern Reference**: Follow existing flags like `PLANNER_KILL_SWITCH: bool = False`

**Environment Variable**: `APPLYLENS_COMPANION_BANDIT_ENABLED=true`

### 2. Wire Flag into Extension Learning Router

**File**: `services/api/app/routers/extension_learning.py`

**Location**: Style hint computation logic (likely in endpoint returning `preferredStyleId`)

```python
from app.config import agent_settings

# In style hint endpoint:
if not agent_settings.COMPANION_BANDIT_ENABLED:
    # Force fallback policy - no bandit exploration
    policy = "fallback"
    style_id_to_use = style_hint.get("preferred_style_id")
else:
    # Normal bandit path: epsilon-greedy exploration
    policy = compute_bandit_policy()  # "exploit", "explore", or "fallback"
    if policy == "explore":
        style_id_to_use = random_explore()
    elif policy == "exploit":
        style_id_to_use = style_hint.get("preferred_style_id")
    else:
        style_id_to_use = style_hint.get("preferred_style_id")

# CRITICAL: Log event regardless of flag state
log_autofill_event(
    style_id=style_id_to_use,
    policy=policy,  # Will be "fallback" when disabled
    # ... other fields
)
```

**Guardrails**:
- ✅ Event logging continues when disabled
- ✅ Policy metric correctly shows "fallback" when disabled
- ✅ Never silently increase exploration rate
- ✅ Fallback matches Phase 5 pre-bandit behavior

### 3. Update Autofill Aggregator

**File**: `services/api/app/autofill_aggregator.py`

**Current State**: Already has `autofill_policy_total{policy="fallback"|"exploit"|"explore"}` metric

**Required Change**: None needed - aggregator continues processing events regardless of policy value

**Verification**: When flag disabled, expect:
```
autofill_policy_total{policy="fallback"} → increments
autofill_policy_total{policy="explore"} → stops incrementing
autofill_policy_total{policy="exploit"} → stops incrementing
```

---

## Extension Implementation

### 1. Add Feature Flag Helper

**Location**: Extension codebase (likely `apps/extension-applylens/src/utils/` or similar)

**File**: Create `featureFlags.ts`:

```typescript
/**
 * Phase 6: Bandit feature flag controls
 *
 * Allows dev/user-level override of bandit behavior via window object.
 * Backend flag takes precedence - extension flag is convenience for testing.
 */

const BANDIT_GLOBAL_DEFAULT_ENABLED = true;

/**
 * Check if bandit-based style selection is enabled.
 *
 * Checks window.__APPLYLENS_BANDIT_ENABLED for dev/user override.
 * If not set, defaults to BANDIT_GLOBAL_DEFAULT_ENABLED (true).
 *
 * Backend will enforce its own flag regardless - this is for extension-side logic only.
 */
export function isBanditEnabled(): boolean {
  if (typeof window !== "undefined" && typeof (window as any).__APPLYLENS_BANDIT_ENABLED === "boolean") {
    return (window as any).__APPLYLENS_BANDIT_ENABLED;
  }
  return BANDIT_GLOBAL_DEFAULT_ENABLED;
}

/**
 * Manually enable bandit for current session (dev testing).
 * Usage in console: window.__APPLYLENS_BANDIT_ENABLED = true
 */
export function enableBandit(): void {
  (window as any).__APPLYLENS_BANDIT_ENABLED = true;
  console.log("[ApplyLens] Bandit learning enabled");
}

/**
 * Manually disable bandit for current session (dev testing).
 * Usage in console: window.__APPLYLENS_BANDIT_ENABLED = false
 */
export function disableBandit(): void {
  (window as any).__APPLYLENS_BANDIT_ENABLED = false;
  console.log("[ApplyLens] Bandit learning disabled - using preferred style only");
}
```

### 2. Guard Bandit Selection Logic

**Location**: Content script or autofill logic (likely `content.js` or `runScanAndSuggest`)

**Before (Phase 5.x)**:
```typescript
// Use bandit-selected style if available
const styleToUse = styleHint?.preferredStyleId || DEFAULT_STYLE;
```

**After (Phase 6)**:
```typescript
import { isBanditEnabled } from './utils/featureFlags';

// Check feature flag before using bandit selection
const styleToUse = isBanditEnabled() && styleHint?.preferredStyleId
  ? styleHint.preferredStyleId
  : DEFAULT_STYLE;
```

**Fallback Behavior**:
- When disabled: Use `DEFAULT_STYLE` constant (likely `"professional_para_v1"`)
- When enabled: Use backend's `preferredStyleId` (may be from bandit or aggregated stats)

---

## Environment Configuration

### Production (.env.prod)

```bash
# Phase 6: Bandit rollout controls
APPLYLENS_COMPANION_BANDIT_ENABLED=true
```

### Development (.env.dev)

```bash
# Phase 6: Disable bandit in dev for controlled testing
APPLYLENS_COMPANION_BANDIT_ENABLED=false
```

### Container Deployment

**Restart API container** after updating .env file:

```bash
docker stop applylens-api-prod
docker run -d \
  --name applylens-api-prod \
  --env-file .env.prod \
  --network applylens_applylens-prod \
  --network-alias applylens-api \
  leoklemet/applylens-api:0.6.0-phase5-fixed
```

**Verification**:
```bash
docker exec applylens-api-prod python -c "from app.config import agent_settings; print(f'Bandit enabled: {agent_settings.COMPANION_BANDIT_ENABLED}')"
```

---

## Testing Procedures

### Backend Flag Test

**Test Enabled State**:
```bash
# Set flag to true
export APPLYLENS_COMPANION_BANDIT_ENABLED=true

# Fetch style hint for test profile
curl https://applylens.app/api/extension/style-hint?host=test.com&schema_hash=abc123

# Expect: Response contains preferredStyleId with varied policy values
```

**Test Disabled State**:
```bash
# Set flag to false
export APPLYLENS_COMPANION_BANDIT_ENABLED=false

# Fetch style hint multiple times
for i in {1..10}; do
  curl -s https://applylens.app/api/extension/style-hint?host=test.com&schema_hash=abc123 \
    | jq -r '.policy'
done

# Expect: All responses show policy="fallback"
```

### Extension Flag Test

**Enable in Browser Console**:
```javascript
// Enable bandit (should already be enabled by default)
window.__APPLYLENS_BANDIT_ENABLED = true;

// Trigger autofill - should use bandit selection
```

**Disable in Browser Console**:
```javascript
// Disable bandit
window.__APPLYLENS_BANDIT_ENABLED = false;

// Trigger autofill - should use DEFAULT_STYLE constant
```

### Metrics Validation

**Check Prometheus metrics** after testing:

```bash
curl https://applylens.app/api/metrics | grep autofill_policy_total
```

**Expected when disabled**:
```
autofill_policy_total{policy="fallback"} 45
autofill_policy_total{policy="explore"} 0
autofill_policy_total{policy="exploit"} 0
```

**Expected when enabled**:
```
autofill_policy_total{policy="fallback"} 10
autofill_policy_total{policy="explore"} 8
autofill_policy_total{policy="exploit"} 27
```

---

## Rollout Strategy

### Phase A: Dark Launch (Week 1)
- Deploy with `COMPANION_BANDIT_ENABLED=false`
- Verify event logging continues
- Check aggregator still updates `preferred_style_id`
- Monitor metrics: `autofill_policy_total{policy="fallback"}` should be 100%

### Phase B: Dev Testing (Week 2)
- Enable for internal users only
- Use extension flag: `window.__APPLYLENS_BANDIT_ENABLED = true`
- Monitor for any unexpected behavior
- Verify exploration rate matches epsilon parameter

### Phase C: Canary (Week 3)
- Enable backend flag: `COMPANION_BANDIT_ENABLED=true`
- Monitor metrics:
  - Exploration rate (~10% if epsilon=0.1)
  - Exploit rate (~80% if good coverage)
  - Fallback rate (~10% for new segments)

### Phase D: Full Rollout (Week 4)
- Monitor for 7 days
- Check that `preferred_style_id` improves over time
- Verify no increase in error rates or user complaints

### Rollback Procedure
If issues detected:
1. **Immediate**: Set `APPLYLENS_COMPANION_BANDIT_ENABLED=false`
2. **Restart API**: `docker restart applylens-api-prod`
3. **Verify**: Check metrics show 100% fallback policy
4. **Investigate**: Review logs for errors during bandit selection

---

## Monitoring & Observability

### Key Metrics

**Bandit Policy Distribution**:
```promql
rate(autofill_policy_total[5m])
```

**Exploration Rate**:
```promql
rate(autofill_policy_total{policy="explore"}[5m])
  /
rate(autofill_policy_total[5m])
```

**Style Choice Distribution**:
```promql
rate(autofill_style_choice_total[5m])
```

### Alerts

**No Exploration Activity** (indicates flag disabled or bandit broken):
```yaml
- alert: BanditNoExploration
  expr: rate(autofill_policy_total{policy="explore"}[10m]) == 0
  for: 30m
  annotations:
    summary: "Bandit exploration stopped - check COMPANION_BANDIT_ENABLED flag"
```

**Excessive Exploration** (indicates epsilon misconfigured):
```yaml
- alert: BanditExcessiveExploration
  expr: |
    rate(autofill_policy_total{policy="explore"}[10m])
      /
    rate(autofill_policy_total[10m]) > 0.25
  for: 15m
  annotations:
    summary: "Bandit exploring >25% - check epsilon parameter"
```

---

## Implementation Checklist

### Backend
- [ ] Add `COMPANION_BANDIT_ENABLED: bool = True` to `AgentSettings`
- [ ] Wire flag into `extension_learning.py` style hint logic
- [ ] Force `policy="fallback"` when disabled
- [ ] Ensure event logging continues regardless of flag
- [ ] Test both enabled and disabled states
- [ ] Verify metrics reflect policy correctly

### Extension
- [ ] Create `featureFlags.ts` with `isBanditEnabled()`
- [ ] Add dev helpers: `enableBandit()`, `disableBandit()`
- [ ] Guard bandit selection with flag check
- [ ] Fallback to `DEFAULT_STYLE` when disabled
- [ ] Test browser console override

### Infrastructure
- [ ] Update `.env.prod` with `APPLYLENS_COMPANION_BANDIT_ENABLED=true`
- [ ] Update `.env.dev` with `APPLYLENS_COMPANION_BANDIT_ENABLED=false`
- [ ] Restart API containers with new env vars
- [ ] Verify flag value via docker exec

### Monitoring
- [ ] Add Prometheus alerts for exploration rate
- [ ] Create Grafana dashboard for policy distribution
- [ ] Document rollback procedures
- [ ] Set up Slack alerts for anomalies

### Documentation
- [ ] Update STYLE_TUNING_RUNBOOK.md with flag instructions
- [ ] Add troubleshooting section for disabled bandit
- [ ] Document dev testing procedures
- [ ] Create rollout checklist

---

## Troubleshooting

### Issue: Bandit not exploring despite flag enabled

**Symptoms**: `autofill_policy_total{policy="explore"}` stays at 0

**Diagnosis**:
1. Check backend flag: `docker exec applylens-api-prod python -c "from app.config import agent_settings; print(agent_settings.COMPANION_BANDIT_ENABLED)"`
2. Check extension flag: `window.__APPLYLENS_BANDIT_ENABLED` in browser console
3. Check epsilon parameter in backend (should be ~0.1 for 10% exploration)

**Solution**:
- If backend flag false: Set `APPLYLENS_COMPANION_BANDIT_ENABLED=true` and restart
- If epsilon 0: Update epsilon parameter in bandit configuration
- If extension flag false: Run `window.__APPLYLENS_BANDIT_ENABLED = true`

### Issue: Too much exploration (>25%)

**Symptoms**: `autofill_policy_total{policy="explore"}` > 25% of total

**Diagnosis**: Epsilon parameter too high

**Solution**:
1. Check epsilon value in `extension_learning.py`
2. Reduce to 0.05-0.15 range (5-15% exploration)
3. Restart API container

### Issue: Events not logging when disabled

**Symptoms**: `autofill_agg_runs_total` stops incrementing

**Diagnosis**: Event logging code incorrectly gated by feature flag

**Solution**:
1. Review `extension_learning.py` - event logging should be **outside** flag check
2. Ensure `log_autofill_event()` called regardless of `agent_settings.COMPANION_BANDIT_ENABLED`
3. Fix and redeploy

---

## References

- **Phase 5 Implementation**: `STYLE_TUNING_RUNBOOK.md`
- **AgentSettings Pattern**: `GOOGLE_OAUTH_DEBUG_GUIDE.md` (APPLYLENS_ prefix)
- **Existing Kill Switches**: `PLANNER_KILL_SWITCH`, `INTELLIGENCE_REPORT_ENABLED`
- **Autofill Aggregator**: `services/api/app/autofill_aggregator.py`
- **Extension Learning**: `services/api/app/routers/extension_learning.py`

---

**Last Updated**: 2025-11-15
**Status**: Ready for Implementation
**Owner**: Leo Klemet
