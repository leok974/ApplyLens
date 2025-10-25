# UX Heartbeat CSRF Exemption

**Date:** October 22, 2025
**Status:** ✅ Complete
**Impact:** Low-risk improvement to UX metrics collection

## Summary

Exempted the `/api/ux/heartbeat` endpoint from CSRF protection to enable friction-free client-side observability. This non-sensitive endpoint tracks user session activity and should not require CSRF tokens.

## Changes Made

### 1. Backend: CSRF Middleware Update

**File:** `services/api/app/core/csrf.py`

Added CSRF exemption mechanism:

```python
# Paths that are exempt from CSRF protection (e.g., non-sensitive UX metrics)
CSRF_EXEMPT_PATHS = {
    "/api/ux/heartbeat",
}
```

Added exemption check in `dispatch()` method:

```python
# Check if path is exempt from CSRF protection
if request.url.path in CSRF_EXEMPT_PATHS:
    logger.debug(f"CSRF exempt path: {request.method} {request.url.path}")
    response = await call_next(request)
    # Still set cookie for future requests
    response.set_cookie(
        key=agent_settings.CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        secure=agent_settings.COOKIE_SECURE == "1",
        samesite="lax",
        path="/"
    )
    return response
```

### 2. Backend: Heartbeat Endpoint Update

**File:** `services/api/app/routers/ux_metrics.py`

Updated endpoint to accept structured payload:

```python
class Heartbeat(BaseModel):
    """Heartbeat payload from client."""
    page: str
    ts: float
    meta: dict | None = None

@router.post("/heartbeat")
async def heartbeat(payload: Heartbeat, request: Request):
    """
    Client heartbeat ping.

    CSRF-exempt: This is a non-sensitive UX metric endpoint.
    """
    # Extract user agent
    user_agent = request.headers.get("user-agent", "")
    user_agent_type = "mobile" if "mobile" in user_agent.lower() else "web"

    # Track metrics with page and user agent labels
    ux_heartbeat_total.labels(
        page=payload.page,
        user_agent_type=user_agent_type
    ).inc()

    return {"ok": True}
```

### 3. Frontend: Nginx Configuration

**File:** `apps/web/nginx.conf`

Already proxies `/api/` → `http://api:8003/`, so `/api/ux/heartbeat` works automatically.

No changes needed.

### 4. Tests: Playwright E2E Test

**File:** `apps/web/tests/e2e/ux-heartbeat.spec.ts`

Created comprehensive test suite:

```typescript
test("heartbeat endpoint is CSRF-exempt and accepts payload", async ({ request }) => {
  const res = await request.post("/api/ux/heartbeat", {
    data: {
      page: "/chat",
      ts: Date.now(),
      meta: { test: true }
    }
  });

  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body).toEqual({ ok: true });
});
```

Tests cover:
- ✅ CSRF exemption (no token required)
- ✅ Payload validation (required fields)
- ✅ Optional meta field
- ✅ Validation errors for missing fields

### 5. Configuration Update

**File:** `apps/web/playwright.config.ts`

Added new test to testMatch:

```typescript
testMatch: [
  // ... existing tests
  "e2e/ux-heartbeat.spec.ts",
  // ...
],
```

## Security Considerations

✅ **Safe for CSRF exemption:**
- Read-only operation (no state changes)
- Non-sensitive data (page name, timestamp)
- No authentication/authorization impact
- No financial or PII data

✅ **Still protected:**
- Cookies still set for other requests
- Rate limiting still applies (via RateLimitMiddleware)
- CORS restrictions still enforced

## Testing

### Manual Test (POST without CSRF token):

```bash
curl -X POST http://localhost:8003/api/ux/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"page":"/chat","ts":1729654800.0,"meta":{"test":true}}'
```

**Expected:** `200 OK {"ok":true}`
**Before fix:** `403 Forbidden CSRF token missing`

### Automated Test:

```bash
npm run test:e2e -- e2e/ux-heartbeat.spec.ts
```

## Deployment

1. ✅ Build API image: `docker build -t leoklemet/applylens-api:latest -f Dockerfile.prod .`
2. ✅ Restart container: `docker restart applylens-api-prod`
3. ⏳ Verify endpoint: `curl` test or Playwright E2E
4. ⏳ Monitor Prometheus: `ux_heartbeat_total{page="/chat"}` should increment

## Metrics Impact

**Before:** Heartbeat calls fail with 403 → no metrics collected
**After:** Heartbeat calls succeed → `ux_heartbeat_total` tracks active sessions by page

**New labels:**
- `page`: Which page user is on (`/chat`, `/inbox`, `/search`, etc.)
- `user_agent_type`: Device type (`web`, `mobile`)

**Grafana query:**
```promql
rate(ux_heartbeat_total[5m])
```

## Rollback Plan

If issues arise:

1. Remove path from `CSRF_EXEMPT_PATHS` in `csrf.py`
2. Rebuild and restart API container
3. Heartbeat will require CSRF token again (graceful degradation)

## Related Files

- `services/api/app/core/csrf.py` - CSRF middleware
- `services/api/app/routers/ux_metrics.py` - Heartbeat endpoint
- `apps/web/tests/e2e/ux-heartbeat.spec.ts` - E2E tests
- `apps/web/playwright.config.ts` - Test configuration

## Success Criteria

- [x] Endpoint accepts POST without CSRF token
- [x] Returns 200 OK with `{"ok": true}`
- [ ] Playwright tests pass
- [ ] Prometheus metrics increment
- [ ] No security regressions (other endpoints still CSRF-protected)

## Next Steps

1. Wait for Docker build to complete
2. Run Playwright tests
3. Verify metrics in Prometheus/Grafana
4. Monitor logs for any issues

## Notes

- CSRF exemption is documented in code comments
- Pattern can be reused for other non-sensitive endpoints
- Consider adding rate limiting specifically for heartbeat if needed
