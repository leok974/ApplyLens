# Cloudflare 502 Toolkit - Quick Start Guide

Complete toolkit for diagnosing and fixing Cloudflare edge cache 502 errors.

## Setup (One-time)

### 1. Get Cloudflare API Token

1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Click "Create Token"
3. Use template: "Edit zone DNS"
4. Add permissions:
   - Zone → DNS → Edit
   - Zone → Zone → Read
   - Zone → Cache Purge → Purge
   - Zone → Zone Settings → Edit
5. Select zone: `applylens.app`
6. Click "Continue to summary" → "Create Token"
7. Copy the token (you won't see it again!)

### 2. Set Environment Variable

**PowerShell (current session):**
```powershell
$env:CF_API_TOKEN = "your_token_here"
```

**PowerShell (persistent - all sessions):**
```powershell
[System.Environment]::SetEnvironmentVariable('CF_API_TOKEN', 'your_token_here', 'User')
```

**Verify:**
```powershell
$env:CF_API_TOKEN  # should show your token
```

### 3. Get Zone and DNS Record IDs

```powershell
# Load the helper module
. .\scripts\cf-dns-tools.ps1

# Print all IDs (save this output!)
CF-PrintIds -Domain "applylens.app"
```

Output will look like:
```
Zone: applylens.app → abc123def456...
applylens.app          A      proxied=True   id=xyz789...
www.applylens.app      CNAME  proxied=True   id=def456...
api.applylens.app      CNAME  proxied=True   id=ghi789...
direct.applylens.app   CNAME  proxied=True   id=jkl012...
```

**Save these IDs** - you'll need them for scripts!

---

## Usage

### Option 1: Quick Verification (Diagnose Issue)

**Check if 502s are from origin or edge:**
```powershell
.\scripts\cf-verify-502.ps1
```

This runs:
- ✅ Origin health check (inside Docker)
- 🌐 Edge status check (6 requests to different POPs)
- 📊 Comprehensive health test (30 requests)

**Interpretation:**
- Origin 200, Edge mixed → **Edge cache issue** (cache purge needed)
- Origin 200, Edge 502 → **Edge cache issue** (nuclear option needed)
- Origin 502, Edge 502 → **Infrastructure issue** (check Docker containers)

---

### Option 2: Nuclear Option (Force Cache Rebuild)

**When to use:** Edge is serving 502s but origin is healthy.

**What it does:** Disables Cloudflare proxy (orange → gray) for 75 seconds, then re-enables it. This forces all edge POPs to rebuild cache from origin.

```powershell
.\scripts\cf-nuclear-option.ps1 -Domain "applylens.app" -RecordName "applylens.app"
```

**Custom wait time:**
```powershell
.\scripts\cf-nuclear-option.ps1 -Domain "applylens.app" -RecordName "applylens.app" -WaitSeconds 90
```

**After running:**
```powershell
# Wait 60-90 seconds, then verify
.\scripts\watch-prod-health.ps1
```

Expected: **≥95% success rate**

---

### Option 3: Cache Management

**Purge all cache:**
```powershell
.\scripts\cf-cache-tools.ps1 -ZoneId "your_zone_id" -PurgeAll
```

**Enable Development Mode** (bypasses cache for 3 hours):
```powershell
.\scripts\cf-cache-tools.ps1 -ZoneId "your_zone_id" -EnableDev
```

**Disable Development Mode:**
```powershell
.\scripts\cf-cache-tools.ps1 -ZoneId "your_zone_id" -DisableDev
```

---

### Option 4: Manual Proxy Toggle (Advanced)

**Load helper functions:**
```powershell
. .\scripts\cf-dns-tools.ps1
```

**Disable proxy (orange → gray):**
```powershell
Toggle-CFProxy -Domain "applylens.app" -RecordName "applylens.app" -Proxied:$false
```

**Wait for DNS propagation:**
```powershell
Start-Sleep -Seconds 75
```

**Re-enable proxy (gray → orange):**
```powershell
Toggle-CFProxy -Domain "applylens.app" -RecordName "applylens.app" -Proxied:$true
```

---

## Monitoring

### Continuous Health Check

**Run once:**
```powershell
.\scripts\watch-prod-health.ps1
```

**Custom parameters:**
```powershell
.\scripts\watch-prod-health.ps1 -Url "https://applylens.app/health" -Tries 50
```

**Exit codes:**
- `0` = Success (≥95% success rate)
- `2` = Failure (<95% success rate)

**Use in CI/CD:**
```powershell
.\scripts\watch-prod-health.ps1
if ($LASTEXITCODE -ne 0) {
  # Send alert (Discord webhook, email, etc.)
  Write-Host "Production health check failed!"
}
```

### GitHub Actions Integration

Add to `.github/workflows/prod-health-check.yml`:

```yaml
name: Production Health Check

on:
  schedule:
    - cron: '*/30 * * * *'  # Every 30 minutes
  workflow_dispatch:

jobs:
  health-check:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run health check
        shell: pwsh
        run: |
          .\scripts\watch-prod-health.ps1 -Tries 20

      - name: Alert on failure
        if: failure()
        uses: appleboy/discord-action@master
        with:
          webhook_id: ${{ secrets.DISCORD_WEBHOOK_ID }}
          webhook_token: ${{ secrets.DISCORD_WEBHOOK_TOKEN }}
          message: "🚨 Production health check failed on applylens.app"
```

---

## Advanced: Direct Hostname Bypass

**Purpose:** Diagnostic hostname that bypasses any Page/Transform Rules on root domain.

### Setup (One-time)

1. **Add DNS record in Cloudflare:**
   - Type: `CNAME`
   - Name: `direct`
   - Target: `08d5feee-f504-47a2-a1f2-b86564900991.cfargotunnel.com`
   - Proxy: ✅ Proxied (orange cloud)

2. **Restart cloudflared:**
   ```powershell
   docker compose -f docker-compose.prod.yml restart cloudflared
   ```

3. **Verify:**
   ```powershell
   curl.exe -I https://direct.applylens.app/health
   ```

### Usage

**When root is flaky but need to test origin:**
```powershell
# Test direct (bypasses root domain rules)
curl.exe https://direct.applylens.app/health

# Compare to root
curl.exe https://applylens.app/health
```

If `direct` is 100% but `applylens.app` is flaky → **Root domain has CF rules affecting it**

---

## Troubleshooting

### "CF_API_TOKEN not set"
```powershell
$env:CF_API_TOKEN = "your_token_here"
```

### "Zone not found"
Check token permissions include Zone:Read for applylens.app

### "Record not found"
Run `CF-PrintIds -Domain "applylens.app"` to see available records

### "Authentication failed"
Token may be expired or revoked. Generate new token in CF dashboard.

### Still seeing 502s after nuclear option
1. Wait 5 more minutes for global propagation
2. Add Cache Bypass rule in CF dashboard (see below)
3. Check if Page Rules or Transform Rules are interfering

---

## Long-term Fixes

### Add Cache Bypass Rule for /health

**Via Cloudflare Dashboard:**

1. Go to: Rules → Cache Rules → Create rule
2. Name: "Bypass health checks"
3. When incoming requests match:
   - Field: `URI Path`
   - Operator: `starts with`
   - Value: `/health`
4. Then:
   - Cache eligibility: **Bypass cache**
5. Save and deploy

**Result:** `/health` will NEVER be cached at edge, preventing future 502 cache issues.

---

## Scripts Reference

| Script | Purpose | Example |
|--------|---------|---------|
| `cf-dns-tools.ps1` | Helper functions (load with `. .\script.ps1`) | `CF-PrintIds -Domain "applylens.app"` |
| `cf-cache-tools.ps1` | Cache purge & dev mode | `.\cf-cache-tools.ps1 -ZoneId "abc" -PurgeAll` |
| `cf-nuclear-option.ps1` | Toggle proxy off/on | `.\cf-nuclear-option.ps1 -Domain "applylens.app" -RecordName "applylens.app"` |
| `cf-verify-502.ps1` | Comprehensive diagnosis | `.\cf-verify-502.ps1` |
| `watch-prod-health.ps1` | Continuous monitoring | `.\watch-prod-health.ps1 -Tries 30` |
| `prod-health-check.ps1` | Docker + public checks | `.\prod-health-check.ps1` |

---

## Quick Command Reference

```powershell
# Setup
$env:CF_API_TOKEN = "your_token_here"
. .\scripts\cf-dns-tools.ps1
CF-PrintIds -Domain "applylens.app"

# Diagnose
.\scripts\cf-verify-502.ps1

# Fix (nuclear option)
.\scripts\cf-nuclear-option.ps1 -Domain "applylens.app" -RecordName "applylens.app"

# Monitor
.\scripts\watch-prod-health.ps1

# Cache management
.\scripts\cf-cache-tools.ps1 -ZoneId "your_zone_id" -PurgeAll
.\scripts\cf-cache-tools.ps1 -ZoneId "your_zone_id" -EnableDev
```

---

## Support

- **Cloudflare API Docs:** https://developers.cloudflare.com/api/
- **Cache Purge:** https://developers.cloudflare.com/cache/how-to/purge-cache/
- **Tunnel Config:** https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- **Internal Docs:** `docs/CLOUDFLARE_502_FIX.md`, `docs/502_EDGE_CACHE_DIAGNOSIS.md`
