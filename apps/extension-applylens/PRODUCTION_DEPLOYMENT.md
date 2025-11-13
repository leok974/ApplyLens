# Production Deployment - Quick Reference

## API Backend (FastAPI)

### Update CORS for Extension
```bash
# In production environment variables:
export CORS_ALLOW_ORIGINS="https://applylens.app,https://www.applylens.app,chrome-extension://*"

# After Chrome Web Store approval, use specific extension ID:
export CORS_ALLOW_ORIGINS="https://applylens.app,https://www.applylens.app,chrome-extension://<YOUR_EXTENSION_ID>"
```

### Remove Dev-Only Guard
```python
# In services/api/app/routers/extension.py
# Comment out or remove the dev_only dependency:

# Before (dev):
@router.post("/applications", dependencies=[Depends(dev_only)])

# After (prod):
@router.post("/applications")  # Add proper auth here
```

### Add Authentication (TODO)
```python
# Replace dev_only with proper OAuth or API key validation
from app.auth import require_auth  # Your auth dependency

@router.post("/applications", dependencies=[Depends(require_auth)])
```

### Restart API
```bash
docker restart applylens-api-prod
```

## Web App (React + Vite)

### Enable Feature Flag
```bash
# In production build config or .env.production:
VITE_FEATURE_COMPANION=1
```

### Update Extension Store URL
```typescript
// In apps/web/src/pages/extension/ExtensionLanding.tsx
// Replace placeholder with real Chrome Web Store URL:

const STORE_URL = "https://chrome.google.com/webstore/detail/applylens-companion/<YOUR_EXTENSION_ID>";
```

### Build and Deploy
```bash
cd apps/web
npm run build
# Upload dist/ to your hosting provider
```

## Cloudflare (Optional WAF Rule)

### Rate Limit Extension Endpoints
```
Rule: Rate limit /api/extension/*
Match: URI Path matches regex "^/api/extension/.*"
Action: Block
When: Rate > 60 requests per minute per IP
```

## Grafana Dashboards

### Add Extension Metrics Panels

**Extension API Usage**:
```promql
sum(rate(http_request_duration_seconds_count{route=~"/api/extension/.*"}[5m])) by (route)
```

**Extension Errors**:
```promql
sum(rate(http_request_duration_seconds_count{route=~"/api/extension/.*",status=~"5.."}[5m]))
```

**Application Logs (24h)**:
```promql
increase(applylens_extension_applications_total[24h])
```

**Outreach Logs (24h)**:
```promql
increase(applylens_extension_outreach_total[24h])
```

## Pre-Launch Smoke Tests

### 1. API Endpoints Available
```bash
curl -s https://api.applylens.app/openapi.json | jq '.paths | keys[]' | grep -E '"/api/profile/me"|"/api/extension/'
```

Expected output:
```
"/api/profile/me"
"/api/extension/applications"
"/api/extension/outreach"
"/api/extension/generate-form-answers"
"/api/extension/generate-recruiter-dm"
```

### 2. CSRF Bypass Working
```bash
curl -i -X POST https://api.applylens.app/api/extension/applications \
  -H 'content-type: application/json' \
  -d '{"company":"SmokeCo","role":"Smoke Tester","source":"browser_extension"}' | head -n 20
```

Expected: HTTP 200 or 401 (auth required), NOT 403 (CSRF)

### 3. Metrics Exposed
```bash
curl -s https://api.applylens.app/metrics | grep -E 'applylens_backfill_runs_total|applylens_csrf_fail_total'
```

Expected: Metric names appear in output

### 4. Web App Routes
```bash
# Extension landing page
curl -s https://applylens.app/extension | grep "ApplyLens Companion"

# Privacy policy
curl -s https://applylens.app/extension/privacy | grep "Privacy Policy"
```

## Post-Launch Monitoring

### Week 1
- Check Chrome Web Store reviews daily
- Monitor Prometheus metrics for errors
- Review user feedback emails
- Watch for rate limit violations

### Week 2+
- Analyze usage patterns (which ATS platforms most popular)
- Review application/outreach logging rates
- Consider adding more ATS platforms based on user requests
- Plan v0.2.0 features

## Rollback Plan

If critical issues arise:

### Disable Extension (Emergency)
1. **Chrome Web Store**: "Unpublish" temporarily
2. **API**: Re-enable `dev_only` guard
3. **Web**: Set `VITE_FEATURE_COMPANION=0`

### Partial Rollback
1. **Keep extension live** but disable specific features
2. **Update manifest** to remove problematic permissions
3. **Submit patch version** (v0.1.1)

## Support Escalation

**User reports extension issues**:
1. Check Chrome Web Store reviews
2. Ask for DevTools console logs
3. Verify API connectivity
4. Check Prometheus metrics for their timeframe

**API issues**:
1. Check Docker logs: `docker logs applylens-api-prod`
2. Review Prometheus alerts
3. Check CORS configuration
4. Verify rate limits not blocking legitimate traffic

## Version Release Process

### For v0.2.0+
1. **Update manifest.json**: Bump version number
2. **Test all features**: Run full test suite
3. **Build package**: `.\pack.ps1`
4. **Submit to Chrome Web Store**: Upload new ZIP
5. **Tag release**: `git tag ext-v0.2.0 && git push --tags`
6. **Update changelog**: Document changes in CHANGELOG.md

## Security Checklist

Before going live:
- [ ] No hardcoded API keys in extension code
- [ ] All API calls use HTTPS
- [ ] CORS configured correctly (not `*`)
- [ ] Rate limiting active on extension endpoints
- [ ] Privacy policy accessible and accurate
- [ ] User data deletion process documented and working
- [ ] No sensitive data logged in console.log()
- [ ] Content Security Policy (CSP) properly configured

## Contact

**Developer**: Leo Klemet
**Email**: leoklemet.pa@gmail.com
**Urgent Issues**: Check #applylens channel (if using team chat)
