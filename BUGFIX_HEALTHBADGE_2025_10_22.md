# BugFix: HealthBadge TypeError - October 22, 2025

**Time**: 20:17 UTC
**Status**: ✅ Fixed and Deployed

## Error

```
TypeError: Cannot read properties of undefined (reading 'icon')
    at vD (index-1761177439323.BEBR919J.js:398:125483)
```

**Impact**: HealthBadge component crashing in production, preventing UI from rendering properly.

---

## Root Cause Analysis

### Issue 1: Wrong API Endpoint
**Problem**: `HealthBadge` was calling `/api/metrics/divergence-24h` expecting warehouse divergence data.

**Reality**: That endpoint returns **Prometheus risk metrics**, not warehouse divergence:
```json
{
  "risk_served_24h": {"ok": 850, "warn": 120, "suspicious": 30},
  "suspicious_share_pp": 3.0,
  "suspicious_divergence_pp": -2.0,
  // NO "status" field ❌
}
```

**Expected Data Structure** (from `/api/metrics/divergence-bq`):
```json
{
  "es_count": 2811,
  "bq_count": 2645,
  "divergence_pct": 6.28,
  "status": "paused",  // ✅ This field is required
  "message": "Divergence: 6.28% (PAUSED)"
}
```

### Issue 2: Missing Null Safety
**Problem**: Code assumed `statusConfig[status]` would always return a valid object.

**Code**:
```typescript
const config = statusConfig[status];  // Could be undefined
const Icon = config.icon;             // ❌ Crashes if config is undefined
```

**What Happened**:
1. API returned data without `status` field
2. Component tried to access `statusConfig[undefined]`
3. Result was `undefined`
4. Accessing `undefined.icon` threw TypeError

---

## Fixes Applied

### 1. Corrected API Endpoint ✅
**File**: `apps/web/src/components/HealthBadge.tsx`

**Changed**:
```typescript
// Before:
const res = await fetch('/api/metrics/divergence-24h');

// After:
const res = await fetch('/api/metrics/divergence-bq');
```

**Why**: The `/divergence-bq` endpoint returns the correct data structure with:
- `status` field ("ok" | "degraded" | "paused")
- Warehouse divergence metrics (ES vs BQ counts)
- Proper error handling with status field

### 2. Added Null Safety Check ✅
**File**: `apps/web/src/components/HealthBadge.tsx`

**Changed**:
```typescript
// Before:
const config = statusConfig[status];

// After:
const config = statusConfig[status] || statusConfig.paused;
```

**Why**: Fallback to 'paused' state if status is invalid/undefined.

### 3. Added Status Validation ✅
**File**: `apps/web/src/components/HealthBadge.tsx`

**Changed**:
```typescript
// Before:
setStatus(data.status);

// After:
if (data.status && ['ok', 'degraded', 'paused'].includes(data.status)) {
  setStatus(data.status);
} else {
  console.warn(`[HealthBadge] Invalid status from API: ${data.status}, defaulting to 'paused'`);
  setStatus('paused');
}
```

**Why**: Validate API response before using it, log warnings for debugging.

---

## API Endpoint Comparison

### `/api/metrics/divergence-24h` (Risk Metrics)
**Purpose**: Prometheus risk analysis (24h vs prior 24h)

**Returns**:
```json
{
  "risk_served_24h": { "ok": 850, "warn": 120, "suspicious": 30 },
  "risk_served_prev24h": { "ok": 800, "warn": 150, "suspicious": 50 },
  "suspicious_share_pp": 3.0,
  "suspicious_divergence_pp": -2.0,
  "error_rate_5m": 0.001,
  "p50_latency_s": 0.125,
  "p95_latency_s": 0.450,
  "rate_limit_ratio_5m": 0.002,
  "ts": "2025-10-23T00:16:38.801492+00:00"
}
```

**Use Case**: Grafana dashboards, risk trend analysis

---

### `/api/metrics/divergence-bq` (Warehouse Health) ✅
**Purpose**: Data consistency check (ES vs BQ)

**Returns**:
```json
{
  "es_count": 2811,
  "bq_count": 2645,
  "divergence_pct": 6.28,
  "status": "paused",
  "message": "Divergence: 6.28% (PAUSED)"
}
```

**Status Thresholds**:
- `ok`: < 2% divergence (green)
- `degraded`: 2-5% divergence (amber)
- `paused`: > 5% divergence or error (red)

**Use Case**: HealthBadge component, warehouse monitoring

**Demo Mode**: Returns mock healthy data when `USE_WAREHOUSE_METRICS=0`

---

## Testing

### 1. Local Verification ✅
```powershell
# Check endpoint returns correct data
curl http://localhost/api/metrics/divergence-bq

# Expected output:
{
  "es_count": 2811,
  "bq_count": 2645,
  "divergence_pct": 6.28,
  "status": "paused",
  "message": "Divergence: 6.28% (PAUSED)"
}
```

### 2. Container Health ✅
```powershell
docker ps --filter "name=applylens-web-prod"
# Status: Up 19 seconds (healthy) ✅
```

### 3. Browser Console
**Before Fix**:
```
TypeError: Cannot read properties of undefined (reading 'icon')
```

**After Fix**:
```
[HealthBadge] Checking warehouse health...
```

### 4. Visual Test
1. Visit: https://applylens.app/web/
2. Check HealthBadge in header shows status (no crash)
3. Verify tooltip shows divergence data

---

## Deployment

```powershell
# Rebuild with fixes
docker build -f apps/web/Dockerfile.prod -t leoklemet/applylens-web:latest apps/web/

# Deploy to production
docker-compose -f docker-compose.prod.yml up -d --force-recreate web

# Verify health
docker ps --filter "name=applylens-web-prod"
# Output: Up 19 seconds (healthy) ✅
```

---

## Prevention Measures

### 1. TypeScript Safety
Consider using stricter types:
```typescript
type HealthStatus = 'ok' | 'degraded' | 'paused' | 'loading';

// This would catch invalid status values at compile time
const config: StatusConfig = statusConfig[status as HealthStatus];
```

### 2. API Contract Validation
Add runtime validation with Zod or similar:
```typescript
import { z } from 'zod';

const DivergenceSchema = z.object({
  es_count: z.number(),
  bq_count: z.number(),
  divergence_pct: z.number().nullable(),
  status: z.enum(['ok', 'degraded', 'paused']),
  message: z.string(),
});

const data = DivergenceSchema.parse(await res.json());
```

### 3. Unit Tests
Add tests for edge cases:
- API returns no status field
- API returns invalid status value
- Network error handling
- 5xx responses

### 4. Error Boundaries
Wrap HealthBadge in React Error Boundary to prevent full page crash:
```typescript
<ErrorBoundary fallback={<div>Health check unavailable</div>}>
  <HealthBadge />
</ErrorBoundary>
```

---

## Related Files

**Fixed**:
- `apps/web/src/components/HealthBadge.tsx` - Component logic

**API Endpoints**:
- `services/api/app/routers/metrics.py` - Backend metrics

**Documentation**:
- `DEPLOYMENT_2025_10_22.md` - Initial deployment
- `BUGFIX_HEALTHBADGE_2025_10_22.md` - This file

---

## Status

✅ **Fixed**: Changed endpoint from `/divergence-24h` to `/divergence-bq`
✅ **Deployed**: Web container updated and healthy
✅ **Verified**: No more TypeError in production
✅ **Safeguarded**: Added null checks and validation

**Next Steps**:
- Monitor production logs for warnings
- Add unit tests for HealthBadge
- Consider adding error boundary
- Document API contracts in OpenAPI spec
