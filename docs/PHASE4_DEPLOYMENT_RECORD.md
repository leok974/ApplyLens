# Phase 4 AI Features - Production Deployment

**Date:** October 20, 2025  
**Status:** ✅ ENABLED  
**Backup:** `.env.production.backup.20251020-145308`

---

## ✅ Feature Flags Enabled

### Configuration Changes

**File:** `apps/web/.env.production`

| Feature | Before | After | Description |
|---------|--------|-------|-------------|
| `VITE_FEATURE_SUMMARIZE` | 0 | **1** | Email summarization with AI |
| `VITE_FEATURE_RISK_BADGE` | 0 | **1** | Risk indicators on emails |
| `VITE_FEATURE_RAG_SEARCH` | 0 | **1** | Semantic/RAG-powered search |
| `VITE_DEMO_MODE` | 0 | 0 | Demo mode (remains disabled) |

---

## 📦 Deployment Steps

### 1. Rebuild Web App

```bash
cd D:\ApplyLens\apps\web
npm run build
```

**Expected output:**
```
vite v5.x.x building for production...
✓ modules transformed
dist/index.html
dist/assets/index-[hash].js
✓ built in X.XXs
```

### 2. Restart Docker Container

```bash
cd D:\ApplyLens
docker compose -f docker-compose.prod.yml up -d --build web
```

**Expected output:**
```
[+] Building X.Xs (X/X) FINISHED
[+] Running 1/1
 ✔ Container applylens-web-prod  Started
```

### 3. Verify Deployment

```bash
# Check container logs
docker logs applylens-web-prod --tail 50

# Check container status
docker ps | grep applylens-web-prod

# Test health
curl -I https://applylens.io
```

---

## ✅ Feature Verification

After deployment, verify each feature:

### 1. Email Summarization
- [ ] Open an email thread with multiple messages
- [ ] Look for "Summarize" button or icon
- [ ] Click and wait for AI summary
- [ ] Verify summary is relevant and concise
- [ ] Check for proper formatting

**Expected behavior:**
- Button appears on emails with 3+ messages
- Summary loads in 2-5 seconds
- Summary is 2-3 paragraphs
- Key points are highlighted

### 2. Risk Badge
- [ ] View email list/inbox
- [ ] Look for risk indicators on emails
- [ ] Verify color coding: 🔴 high, 🟡 medium, 🟢 low
- [ ] Hover over badge for details
- [ ] Check risk score is accurate

**Expected behavior:**
- Badges appear on all emails
- Colors match risk level
- Tooltip shows risk factors
- Updates in real-time

### 3. RAG Search
- [ ] Open search interface
- [ ] Try natural language query (e.g., "emails about budget")
- [ ] Verify semantic results appear
- [ ] Check result relevance
- [ ] Test follow-up questions

**Expected behavior:**
- Natural language queries work
- Results include context snippets
- Response time < 2 seconds
- Relevant results ranked first

---

## 🔍 Browser Console Verification

Open browser console at your production site:

```javascript
// Check feature flags are loaded
console.log(import.meta.env.VITE_FEATURE_SUMMARIZE)   // Should be "1"
console.log(import.meta.env.VITE_FEATURE_RISK_BADGE)  // Should be "1"
console.log(import.meta.env.VITE_FEATURE_RAG_SEARCH)  // Should be "1"
console.log(import.meta.env.VITE_DEMO_MODE)           // Should be "0"
```

---

## 📊 Monitoring

### Key Metrics to Watch

**Performance:**
- Page load time (should remain < 2s)
- Time to interactive (should remain < 3s)
- API response times (check Grafana)

**Errors:**
- JavaScript errors in browser console
- API errors in server logs
- Failed AI requests

**Usage:**
- Feature adoption rate
- User engagement with AI features
- Feedback/support tickets

### Grafana Dashboard

Monitor at: http://localhost:3000/d/applylens-phase4-overview

Watch for:
- Increased API calls to AI endpoints
- Response time spikes
- Error rate changes
- Resource utilization

### Log Monitoring

```bash
# Watch API logs for AI features
docker logs -f applylens-api-prod | grep -E "summarize|risk|rag"

# Watch for errors
docker logs -f applylens-api-prod | grep -i error

# Watch web container
docker logs -f applylens-web-prod
```

---

## 🔄 Rollback Plan

If issues occur, quickly rollback:

### Quick Rollback

```bash
# 1. Restore backup
cd D:\ApplyLens\apps\web
Copy-Item .env.production.backup.20251020-145308 .env.production -Force

# 2. Rebuild
npm run build

# 3. Restart
cd D:\ApplyLens
docker compose -f docker-compose.prod.yml up -d --build web
```

### Or: Disable Specific Feature

Edit `apps/web/.env.production` and change the problematic feature to `0`:

```bash
VITE_FEATURE_SUMMARIZE=0  # If summarization has issues
VITE_FEATURE_RISK_BADGE=0  # If risk badges have issues
VITE_FEATURE_RAG_SEARCH=0  # If RAG search has issues
```

Then rebuild and restart.

---

## 📋 Post-Deployment Checklist

### Immediate (First Hour)
- [ ] Web container rebuilt and running
- [ ] No errors in container logs
- [ ] Website accessible
- [ ] All 3 features visible in UI
- [ ] Browser console shows correct flags
- [ ] Quick functional test of each feature

### First 24 Hours
- [ ] Monitor error rates in logs
- [ ] Check Grafana for anomalies
- [ ] Review user feedback channels
- [ ] Test on different browsers
- [ ] Verify mobile responsiveness
- [ ] Check API rate limits not exceeded

### First Week
- [ ] Analyze feature adoption metrics
- [ ] Review performance impact
- [ ] Collect user feedback
- [ ] Identify common issues
- [ ] Plan improvements/fixes

---

## 🐛 Common Issues & Solutions

### Issue: Features not appearing in UI

**Solution:**
1. Check browser console for build errors
2. Hard refresh (Ctrl+Shift+R)
3. Clear browser cache
4. Verify `.env.production` was used in build
5. Check build output for warnings

### Issue: AI features timing out

**Solution:**
1. Check API logs for errors
2. Verify API container is healthy
3. Check network connectivity
4. Review rate limiting settings
5. Increase timeout values if needed

### Issue: Incorrect risk scores

**Solution:**
1. Check API endpoint `/api/security/risk/*`
2. Verify ML model is loaded
3. Review risk calculation logic
4. Check training data freshness
5. Re-train model if needed

---

## 📁 Files Modified

1. **apps/web/.env.production** - Feature flags enabled
2. **apps/web/.env.production.backup.20251020-145308** - Backup created
3. **docs/PHASE4_DEPLOYMENT_RECORD.md** - This file

---

## 🎯 Success Criteria

Deployment is successful when:

- ✅ All 3 features enabled and visible
- ✅ No increase in error rates
- ✅ Performance remains stable
- ✅ User feedback is positive
- ✅ No critical bugs reported
- ✅ API metrics healthy in Grafana

---

## 📞 Support

**If issues occur:**
1. Check this document's troubleshooting section
2. Review logs: `docker logs applylens-api-prod --tail 100`
3. Check Grafana: http://localhost:3000/d/applylens-phase4-overview
4. Consider rollback if critical
5. Document issue for post-mortem

---

## 📊 Current Status

**Features:** ✅ ENABLED in configuration  
**Deployment:** ⏳ Pending rebuild and restart  
**Backup:** ✅ Created  
**Rollback:** ✅ Ready if needed

---

**Next Action:** Run the deployment steps above to activate the features.

---

**Deployment Record Created:** October 20, 2025 14:53  
**Enabled By:** Production deployment process  
**Environment:** Production (`docker-compose.prod.yml`)
