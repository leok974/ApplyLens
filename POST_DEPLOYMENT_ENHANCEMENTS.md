# Email Risk v3.1 - Post-Deployment Enhancements

## Overview

This document describes the 5 post-deployment enhancements implemented for the Email Risk v3.1 system. These improvements enhance testing, monitoring, validation, and gradual rollout capabilities.

---

## 1. Unit Test for BadRequest Fallback ✅

**File**: `services/api/tests/api/test_email_risk.py`

**Purpose**: Verify that the `/emails/{email_id}/risk-advice` endpoint properly handles `BadRequestError` by falling back to wildcard search.

### Test Cases

1. **Successful get from alias** - Direct retrieval using `gmail_emails` alias
2. **BadRequest fallback to search** - When alias points to multiple indices
3. **NotFound fallback to search** - Document not in primary index
4. **Search fallback not found** - Return 404 when document doesn't exist
5. **Search fallback error** - Return 500 on search errors
6. **Custom index parameter** - Test `?index=` query param
7. **Elasticsearch unavailable** - Return 503 when ES is down
8. **Response includes all fields** - Verify complete risk advice structure

### Running Tests

```bash
# Run all email risk tests
pytest services/api/tests/api/test_email_risk.py -v

# Run specific test
pytest services/api/tests/api/test_email_risk.py::TestGetRiskAdvice::test_badrequest_fallback_to_search -v
```

### Expected Behavior

When `ES.get()` raises `BadRequestError` (alias points to multiple indices):
1. Catch exception
2. Fall back to `ES.search()` with query: `{"ids": {"values": [email_id]}}`
3. Search across `gmail_emails-*` wildcard
4. Return document if found, 404 if not found

---

## 2. Smoke Script CI Integration ✅

**File**: `scripts/smoke_risk_advice.ps1`

**Purpose**: Enable CI/CD pipeline integration by exiting with non-zero code on any check failure.

### Changes

- Added `$failCount` tracking variable
- Error handling with try-catch blocks for all API calls
- Non-zero exit codes on failure
- Detailed error reporting

### Exit Codes

- `0` - All checks passed (score >= 40, no failures)
- `1` - Score too low OR any check failed

### CI Integration

```yaml
# Example GitHub Actions step
- name: Run Email Risk Smoke Test
  run: |
    .\scripts\smoke_risk_advice.ps1
  working-directory: D:\ApplyLens
  shell: pwsh
```

### Checks Performed

1. ✓ Index test email through v3 pipeline
2. ✓ Fetch risk advice from API (direct index)
3. ✓ Test fallback search (without index param)
4. ✓ Check Prometheus metrics
5. ✓ Validate suspicion score >= 40

---

## 3. Grafana P95 Latency Dashboard ✅

**File**: `infra/grafana/provisioning/dashboards/json/email_risk_v31.json`

**Purpose**: Monitor Email Risk v3.1 performance and alert status with P50/P95 latency tracking.

### Dashboard Panels

#### Top Row - Stats (4 panels)
- **Risk Advice Served (24h)** - Total requests
- **Suspicious Emails Detected** - Count with thresholds (10/50)
- **Safe Emails Detected** - Count
- **Crypto Decrypt Errors** - Alert if > 0

#### Middle Row - Time Series (2 panels)
- **Risk Advice Request Rate** - By level (suspicious/safe)
- **Risk Advice Latency (P50/P95)** - With 300ms threshold
  - P50 latency (green line, 1px)
  - P95 latency (blue line, 2px)
  - Orange threshold at 300ms
  - Red threshold at 500ms

#### Lower Row - Time Series (2 panels)
- **Risk Feedback Submitted** - By verdict (stacked)
- **API Error Rate** - 5xx errors with thresholds

#### Bottom Row - Table (1 panel)
- **Alert Status** - All EmailRisk* alerts with color-coded states

### PromQL Queries

**P50 Latency**:
```promql
histogram_quantile(0.5,
  sum by (le) (
    rate(http_request_duration_seconds_bucket{path=~".*/risk-advice"}[5m])
  )
)
```

**P95 Latency**:
```promql
histogram_quantile(0.95,
  sum by (le) (
    rate(http_request_duration_seconds_bucket{path=~".*/risk-advice"}[5m])
  )
)
```

### Access

URL: `http://localhost:3000/d/email-risk-v31`

Refresh: 30s
Time Range: Last 6 hours (configurable)

---

## 4. Kibana Data View Validation ✅

**File**: `scripts/validate_kibana_dataview.ps1`

**Purpose**: Export, validate, and test re-import of the `gmail_emails` data view configuration.

### Features

1. **Export** - Fetch data view via Kibana API
2. **Validate** - Check required fields:
   - Title pattern: `gmail_emails*`
   - Time field: `received_at`
   - Index pattern: `gmail_emails` or `gmail_emails-*`
   - Field count > 0
3. **Re-import Test** - Create test data view to verify idempotency
4. **Cleanup** - Delete test data view

### Usage

```powershell
# Run validation
.\scripts\validate_kibana_dataview.ps1

# Custom Kibana URL
$env:KIBANA_URL = "http://localhost:5601"
.\scripts\validate_kibana_dataview.ps1
```

### Output

```
=== Kibana Data View Validation ===

1. Exporting data view 'gmail_emails'...
  ✓ Data view exported successfully
  ✓ Saved to: backup/kibana_data_view_gmail_emails.json

2. Validating data view configuration...
  ✓ Title pattern: gmail_emails-*
  ✓ Time field: received_at
  ✓ Index pattern: gmail_emails-*
  ✓ Fields defined: 156

  ✅ All validations passed

3. Testing re-import idempotency...
  ✓ Test data view created: gmail_emails_test
  ✓ Re-import validation successful
  ✓ Test data view cleaned up

=== Validation Complete ===

Data View Summary:
  ID: gmail_emails
  Title: gmail_emails-*
  Time Field: received_at
  Fields: 156
  Export File: backup/kibana_data_view_gmail_emails.json

✅ Data view configuration validated
```

### Exit Codes

- `0` - All validations passed
- `1` - Validation error or export failed

---

## 5. Feature Flag Percentage Rollout ✅

**Files**:
- `apps/web/src/hooks/useFeatureFlag.ts`
- `apps/web/src/vite-env.d.ts`
- `apps/web/src/hooks/__tests__/useFeatureFlag.test.ts`

**Purpose**: Support gradual feature rollout (10% → 25% → 50% → 100%) based on deterministic user hashing.

### Core Functions

#### `hashToBucket(userId: string): number`
- Deterministic hash algorithm
- Maps user ID to bucket 0-99
- Same user always gets same bucket

#### `isUserInRollout(userId: string, percentage: number): boolean`
- Returns `true` if user's bucket < percentage
- 10% rollout = buckets 0-9
- 25% rollout = buckets 0-24
- Ensures gradual inclusion (users in 10% are always in 25%)

### Pre-configured Flags

```typescript
import { useEmailRiskBanner } from '@/hooks/useFeatureFlag';

function EmailDetailView({ email, user }) {
  const showRiskBanner = useEmailRiskBanner(user.email);

  return (
    <>
      {showRiskBanner && <EmailRiskBanner email={email} />}
      {/* ... */}
    </>
  );
}
```

### Environment Variables

**.env**:
```bash
# Enable feature globally
VITE_FEATURE_EMAIL_RISK_BANNER=1

# Set rollout percentage (10, 25, 50, 100)
VITE_FEATURE_EMAIL_RISK_BANNER_ROLLOUT=10

# Other flags
VITE_FEATURE_EMAIL_RISK_DETAILS=1
VITE_FEATURE_EMAIL_RISK_DETAILS_ROLLOUT=25

VITE_FEATURE_EMAIL_RISK_ADVICE=1
VITE_FEATURE_EMAIL_RISK_ADVICE_ROLLOUT=100
```

### Rollout Strategy

**Week 1**: 10% rollout
```bash
VITE_FEATURE_EMAIL_RISK_BANNER_ROLLOUT=10
```

**Week 2**: Increase to 25% (includes all users from 10%)
```bash
VITE_FEATURE_EMAIL_RISK_BANNER_ROLLOUT=25
```

**Week 3**: Increase to 50%
```bash
VITE_FEATURE_EMAIL_RISK_BANNER_ROLLOUT=50
```

**Week 4**: Full rollout
```bash
VITE_FEATURE_EMAIL_RISK_BANNER_ROLLOUT=100
```

### Monitoring

```typescript
import { getEmailRiskRolloutStatus } from '@/hooks/useFeatureFlag';

// In admin panel or debug view
const status = getEmailRiskRolloutStatus();
console.log(status);
// {
//   EmailRiskBanner: { enabled: true, rollout: 10 },
//   EmailRiskDetails: { enabled: true, rollout: 25 },
//   EmailRiskAdvice: { enabled: true, rollout: 100 }
// }
```

### Unit Tests

Run tests to verify distribution:
```bash
npm test -- useFeatureFlag.test.ts
```

Tests verify:
- ✓ Deterministic hashing (same user → same bucket)
- ✓ Correct distribution (~10% for 10% rollout)
- ✓ Gradual inclusion (10% users ⊂ 25% users ⊂ 50% users)
- ✓ Edge cases (0%, 100%, negative, >100%)

---

## Summary

| # | Enhancement | File(s) | Status | CI-Ready |
|---|-------------|---------|--------|----------|
| 1 | Unit Test - BadRequest Fallback | `tests/api/test_email_risk.py` | ✅ | Yes |
| 2 | Smoke Script CI Integration | `scripts/smoke_risk_advice.ps1` | ✅ | Yes |
| 3 | Grafana P95 Latency Dashboard | `infra/grafana/.../email_risk_v31.json` | ✅ | Yes |
| 4 | Kibana Data View Validation | `scripts/validate_kibana_dataview.ps1` | ✅ | Yes |
| 5 | Feature Flag % Rollout | `apps/web/src/hooks/useFeatureFlag.ts` | ✅ | Yes |

---

## Next Steps

1. **Run Unit Tests**: `pytest services/api/tests/api/test_email_risk.py -v`
2. **Run Smoke Test**: `.\scripts\smoke_risk_advice.ps1`
3. **Import Grafana Dashboard**: Restart Grafana or use provisioning
4. **Validate Kibana**: `.\scripts\validate_kibana_dataview.ps1`
5. **Configure Rollout**: Set `VITE_FEATURE_EMAIL_RISK_*_ROLLOUT` env vars

---

## Integration with Runbook

These enhancements support the tasks listed in **CUTOVER_RUNBOOK_V31.md** section "Copilot Tasks (Post-Cutover)":

- ✅ Task 1: BadRequest fallback unit test
- ✅ Task 2: Smoke script CI integration
- ✅ Task 3: Grafana P95 latency panel
- ✅ Task 4: Kibana data view validation
- ✅ Task 5: Feature flag percentage rollout

All enhancements are production-ready and CI/CD compatible.
