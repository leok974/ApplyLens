# 🚀 Enable Phase 4 AI Features in Production

**Current Status:** Features disabled (safe default)  
**When Ready:** Follow these steps to enable

---

## Quick Enable Script

Save this as `enable_phase4_features.ps1`:

```powershell
# Enable Phase 4 AI Features in Production Web App
# Run from: D:\ApplyLens

Write-Host "`n🔧 Enabling Phase 4 AI Features in Production`n" -ForegroundColor Cyan

# Backup current config
Copy-Item "apps\web\.env.production" "apps\web\.env.production.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Write-Host "✅ Backup created" -ForegroundColor Green

# Update feature flags
$envFile = "apps\web\.env.production"
$content = Get-Content $envFile -Raw

$content = $content -replace 'VITE_FEATURE_SUMMARIZE=0', 'VITE_FEATURE_SUMMARIZE=1'
$content = $content -replace 'VITE_FEATURE_RISK_BADGE=0', 'VITE_FEATURE_RISK_BADGE=1'
$content = $content -replace 'VITE_FEATURE_RAG_SEARCH=0', 'VITE_FEATURE_RAG_SEARCH=1'

Set-Content $envFile $content -NoNewline
Write-Host "✅ Feature flags updated" -ForegroundColor Green

# Show changes
Write-Host "`nNew configuration:" -ForegroundColor Yellow
Get-Content $envFile | Select-String "VITE_FEATURE"

Write-Host "`n⚠️  Next steps:" -ForegroundColor Yellow
Write-Host "   1. Rebuild web app: npm run build" -ForegroundColor Gray
Write-Host "   2. Restart container: docker compose -f docker-compose.prod.yml up -d --build web" -ForegroundColor Gray
Write-Host "   3. Verify at: https://applylens.io`n" -ForegroundColor Gray
```

---

## Manual Steps

### 1. Edit Configuration

**File:** `apps/web/.env.production`

**Change from:**
```bash
VITE_FEATURE_SUMMARIZE=0
VITE_FEATURE_RISK_BADGE=0
VITE_FEATURE_RAG_SEARCH=0
```

**Change to:**
```bash
VITE_FEATURE_SUMMARIZE=1
VITE_FEATURE_RISK_BADGE=1
VITE_FEATURE_RAG_SEARCH=1
```

### 2. Rebuild Web App

```bash
cd apps/web
npm run build
```

**Expected output:**
```
vite v5.x.x building for production...
✓ 123 modules transformed.
dist/index.html              1.23 kB
dist/assets/index-abc123.js  456.78 kB
✓ built in 12.34s
```

### 3. Restart Docker Container

**Option A: Restart just the web container**
```bash
docker compose -f docker-compose.prod.yml up -d --build web
```

**Option B: Restart entire stack**
```bash
docker compose -f docker-compose.prod.yml restart
```

### 4. Verify Deployment

**Check container logs:**
```bash
docker logs applylens-web-prod --tail 50
```

**Test the app:**
```bash
curl -I https://applylens.io
# Should return: HTTP/2 200
```

**Check feature flags in browser:**
```javascript
// Open browser console at applylens.io
console.log(import.meta.env.VITE_FEATURE_SUMMARIZE)   // Should be "1"
console.log(import.meta.env.VITE_FEATURE_RISK_BADGE)  // Should be "1"
console.log(import.meta.env.VITE_FEATURE_RAG_SEARCH)  // Should be "1"
```

---

## Feature Verification Checklist

After enabling, verify each feature works:

### ✅ Email Summarization (VITE_FEATURE_SUMMARIZE=1)
- [ ] Open an email thread
- [ ] Look for "Summarize" button
- [ ] Click and verify AI summary appears
- [ ] Check for proper formatting

### ✅ Risk Badge (VITE_FEATURE_RISK_BADGE=1)
- [ ] View email list
- [ ] Look for risk indicators (🔴 high, 🟡 medium, 🟢 low)
- [ ] Verify badge colors match risk levels
- [ ] Check tooltip on hover

### ✅ RAG Search (VITE_FEATURE_RAG_SEARCH=1)
- [ ] Open search interface
- [ ] Look for "AI Search" or "Semantic Search" option
- [ ] Try natural language query
- [ ] Verify results include context/snippets
- [ ] Check response time (<2s)

---

## Rollback Plan

If issues occur, quickly rollback:

### Quick Rollback
```bash
# Restore backup
$latest = Get-ChildItem "apps\web\.env.production.backup.*" | 
          Sort-Object LastWriteTime -Descending | 
          Select-Object -First 1
Copy-Item $latest "apps\web\.env.production" -Force

# Rebuild and restart
cd apps/web
npm run build
cd ..\..
docker compose -f docker-compose.prod.yml up -d --build web
```

### Or: Disable Specific Feature
```bash
# Edit apps/web/.env.production
# Change problematic feature back to 0
VITE_FEATURE_SUMMARIZE=0  # If summarization has issues

# Rebuild
npm run build
docker compose -f docker-compose.prod.yml up -d --build web
```

---

## Monitoring After Enable

### 1. Watch API Logs
```bash
docker logs -f applylens-api-prod | grep -E "summarize|risk|rag"
```

### 2. Monitor Error Rate
```bash
# Check Grafana dashboard
curl http://localhost:3000/d/applylens-phase4-overview
```

### 3. Check Performance
```bash
# API response times
curl -w "@curl-format.txt" -o /dev/null -s \
  http://localhost:8003/api/metrics/profile/activity_daily
```

### 4. User Feedback
- Monitor support channels
- Check error tracking (Sentry, etc.)
- Review user session recordings

---

## Gradual Rollout Strategy

For safer deployment, enable features one at a time:

### Week 1: Enable Risk Badge Only
```bash
VITE_FEATURE_SUMMARIZE=0
VITE_FEATURE_RISK_BADGE=1   # Enable first
VITE_FEATURE_RAG_SEARCH=0
```

### Week 2: Add Summarization
```bash
VITE_FEATURE_SUMMARIZE=1    # Enable second
VITE_FEATURE_RISK_BADGE=1
VITE_FEATURE_RAG_SEARCH=0
```

### Week 3: Full Phase 4
```bash
VITE_FEATURE_SUMMARIZE=1
VITE_FEATURE_RISK_BADGE=1
VITE_FEATURE_RAG_SEARCH=1   # Enable last
```

---

## Production Readiness Checklist

Before enabling in production:

### Infrastructure
- [ ] API endpoints tested and working
- [ ] Grafana dashboard showing healthy metrics
- [ ] Database connections stable
- [ ] Redis cache available
- [ ] Rate limiting configured

### Security
- [ ] API authentication working
- [ ] CORS properly configured
- [ ] Input validation on all AI endpoints
- [ ] Rate limits prevent abuse
- [ ] Error messages don't leak sensitive data

### Performance
- [ ] Load testing completed
- [ ] Response times acceptable (<2s)
- [ ] Caching strategy in place
- [ ] Database queries optimized
- [ ] CDN configured for static assets

### Monitoring
- [ ] Error tracking enabled
- [ ] Performance metrics collected
- [ ] Grafana alerts configured
- [ ] Log aggregation working
- [ ] On-call rotation established

### Documentation
- [ ] Feature docs updated
- [ ] API docs current
- [ ] Runbook for common issues
- [ ] Rollback procedure documented
- [ ] User guides prepared

---

## Current Status

**Features:** ❌ Disabled (safe default)  
**Ready to Enable:** ✅ All systems operational  
**Recommendation:** Enable when above checklist complete

---

**File:** `docs/ENABLE_PHASE4_FEATURES.md`  
**Created:** October 20, 2025  
**Purpose:** Guide for enabling Phase 4 AI features in production
