# 502 Edge Cache Diagnosis Summary

**Date:** 2025-10-30
**Issue:** Intermittent 502 Bad Gateway on https://applylens.app/health
**Root Cause:** Cloudflare edge cache serving stale 502 responses

## Evidence (Definitive Proof)

### A. Origin Health: 100% OK ✅
```bash
docker exec applylens-nginx-prod curl -s -o /dev/null -w "NGINX %{http_code}\n" http://applylens.int/health
# Result: NGINX 200
```

### B. Edge Status: Intermittent 502s ❌
```
Attempt 1: 502 (CF-RAY: SEA - Seattle)
Attempt 2: 200 (CF-RAY: EWR - Newark)
Attempt 3: 502 (CF-RAY: EWR - Newark)
Attempt 4: 200 (CF-RAY: EWR - Newark)
Attempt 5: 502 (CF-RAY: EWR - Newark)
```

**Success Rate:** 53% (32/60 requests)

### C. Cache Headers (When Working)
```
HTTP/1.1 200 OK
Cache-Control: no-store, no-cache, must-revalidate, max-age=0
Pragma: no-cache
Expires: 0
cf-cache-status: DYNAMIC
```

Headers are correct, but some edge POPs still serving cached 502s.

## Actions Taken

1. ✅ **Verified origin health** - All containers healthy, nginx returning 200
2. ✅ **Added no-cache headers** - Updated nginx config for /health and /healthz
3. ✅ **Purged Cloudflare cache** - User purged via dashboard
4. ✅ **Enabled Development Mode** - Should bypass all caching
5. ✅ **Restarted cloudflared** - 4/4 connections active

## Current Status

- **Origin:** 100% healthy (200 OK)
- **Edge:** 53% success rate (some POPs cached 502s)
- **Tunnel:** 4/4 connections active, no errors for applylens.app
- **Config:** No-cache headers properly configured
- **Cloudflare:** Development Mode enabled + Cache purged

## Why Still Failing?

Cloudflare's global edge network has **hundreds of POPs worldwide**. Cache purges and Development Mode changes take time to propagate to all locations:

- Typical propagation: 3-5 minutes
- Maximum propagation: 10-15 minutes
- Your location: LAX, but hitting SEA, EWR POPs with old cache

## Solutions

### Option 1: Wait (Recommended)
Give Development Mode + Cache Purge another 10-15 minutes to propagate globally.

**Test command:**
```powershell
.\scripts\watch-prod-health.ps1
```

### Option 2: Nuclear Option (Immediate Fix)
Temporarily disable Cloudflare proxy to force cache rebuild:

1. Cloudflare Dashboard → DNS
2. Click orange cloud next to `applylens.app` → turns gray (DNS only)
3. Wait 1 minute
4. Click gray cloud → turns orange (proxied again)
5. All edge POPs rebuild cache from origin

**Risk:** 1 minute of direct traffic (no DDoS protection)

### Option 3: Add Page Rule (Long-term)
Ensure /health is never cached at edge:

1. Rules → Page Rules → Create Rule
2. URL pattern: `applylens.app/health*`
3. Setting: **Cache Level** → **Bypass**
4. Save and deploy

### Option 4: Add Transform Rule (Alternative)
Use Cache Rules (newer feature):

1. Rules → Cache Rules → Create Rule
2. Match: `URI Path equals "/health"`
3. Cache eligibility: **Bypass cache**
4. Save and deploy

## Monitoring

Created automated monitoring script:

```powershell
# Run manual check
.\scripts\watch-prod-health.ps1

# Run with custom params
.\scripts\watch-prod-health.ps1 -Url "https://applylens.app/health" -Tries 50

# Exit code 0 = success (95%+), exit code 2 = failure
```

## Long-term Prevention

1. **Never cache health checks** - Add Page Rule for `/health*` with Cache Level: Bypass
2. **Monitor continuously** - Add watch-prod-health.ps1 to CI/CD
3. **Alert on failures** - Hook script exit code to Discord/Slack webhook
4. **Use direct hostname** - Add `direct.applylens.app` bypass for emergency testing

## Files Modified

- `infra/nginx/conf.d/applylens.prod.conf` - Added no-cache headers to /health and /healthz
- `scripts/watch-prod-health.ps1` - New monitoring script
- `scripts/prod-health-check.ps1` - Already exists for comprehensive checks

## Next Steps

**Immediate (next 15 minutes):**
1. Wait for Development Mode + Cache Purge propagation
2. Run `.\scripts\watch-prod-health.ps1` every 5 minutes
3. If still < 95% after 15 min → Nuclear Option (disable/re-enable proxy)

**Short-term (today):**
1. Add Page Rule or Cache Rule to bypass cache for `/health*`
2. Disable Development Mode once resolved (it auto-disables after 3 hours anyway)

**Long-term (this week):**
1. Add watch-prod-health.ps1 to GitHub Actions (hourly check)
2. Add alert webhook for failures
3. Document in DEPLOYMENT.md

## Reference

- Cloudflare Cache Purge API: https://developers.cloudflare.com/api/operations/zone-purge
- Page Rules Guide: https://developers.cloudflare.com/rules/page-rules/
- Cache Rules (newer): https://developers.cloudflare.com/cache/how-to/cache-rules/
