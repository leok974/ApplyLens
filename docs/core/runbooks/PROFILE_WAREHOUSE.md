# Profile Page Warehouse Integration - Quick Reference

## What Changed

Profile page (`/profile`) now pulls real data from BigQuery warehouse instead of showing placeholders.

**Endpoint**: `GET /api/metrics/profile/summary`
**Cache**: 60 seconds
**Frontend**: Complete component rewrite
**Tests**: New Playwright suite

---

## Quick Test

### Backend (Dev)
```bash
curl http://localhost:8000/api/metrics/profile/summary | jq
```

**Expected**:
```json
{
  "account": "leoklemet.pa@gmail.com",
  "totals": {
    "all_time_emails": 1234,
    "last_30d_emails": 567
  },
  "top_senders_30d": [...],
  "top_categories_30d": [...],
  "top_interests": [...]
}
```

### Frontend (Dev)
```bash
cd apps/web
npm run dev
# Navigate to: http://localhost:5173/profile
```

**Verify**:
- ✅ 4 cards visible (Activity, Senders, Categories, Interests)
- ✅ Real numbers (not zeros)
- ✅ "Data powered by BigQuery warehouse" badge

### Playwright Tests
```bash
cd apps/web
npm run test:e2e -- profile-warehouse.spec.ts
```

**Expected**: 4/4 tests pass

---

## Production Verification

### Health Check
```bash
curl https://production.applylens.com/api/metrics/profile/summary \
  -H "Cookie: session=..." | jq '.totals'
```

### Web UI
1. Navigate to: https://production.applylens.com/profile
2. Verify all 4 cards load
3. Check browser console for errors
4. Verify numbers match BigQuery

### Logs
```bash
# API logs (check for errors)
docker-compose logs -f api | grep "profile_summary"

# Web logs (check for 404s)
docker-compose logs -f web | grep "/profile"
```

---

## Troubleshooting

### "No data yet" on all cards

**Symptoms**: Cards show "No data yet" but should have data

**Causes**:
1. BigQuery marts empty (Fivetran sync failed)
2. USE_WAREHOUSE_METRICS=0 (feature flag off)
3. Cache returning stale empty state

**Fixes**:
```bash
# Check Fivetran sync
curl http://localhost:8000/api/metrics/profile/freshness

# Check feature flag
docker-compose exec api env | grep WAREHOUSE

# Clear cache
docker-compose restart api
```

### 500 errors on summary endpoint

**Symptoms**: API returns 500, UI shows error banner

**Causes**:
1. BigQuery auth failure (GCP_PROJECT env var missing)
2. Table not found (mart doesn't exist)
3. Query timeout

**Fixes**:
```bash
# Check BigQuery connection
docker-compose exec api python -c "
from google.cloud import bigquery
client = bigquery.Client()
print(client.project)
"

# Check tables exist
bq ls GCP_PROJECT:gmail_marts

# Check logs
docker-compose logs api | grep "Error fetching"
```

### Slow response times

**Symptoms**: Page takes > 2 seconds to load

**Causes**:
1. Cold cache (first request after restart)
2. Large mart tables (millions of rows)
3. BigQuery region latency

**Fixes**:
```bash
# Increase cache TTL (restart required)
# In docker-compose.prod.yml, add:
environment:
  - SUMMARY_CACHE_TTL=300  # 5 minutes

# Check cache hit rate
docker-compose logs api | grep "cache_get.*profile_summary"
```

### Empty interests array

**Symptoms**: Activity/Senders/Categories work, but Interests empty

**Cause**: Keyword extraction query failed (non-critical)

**Fix**:
```bash
# Check logs for specific error
docker-compose logs api | grep "Error fetching top interests"

# Verify stg_gmail__messages table exists
bq show GCP_PROJECT:gmail_raw_stg_gmail_raw_stg.stg_gmail__messages
```

---

## Rollback

If critical issues occur:

```bash
# Stop containers
docker-compose -f docker-compose.prod.yml down

# Edit docker-compose.prod.yml
# Change versions back to v0.4.49:
#   api: leoklemet/applylens-api:v0.4.49
#   web: leoklemet/applylens-web:v0.4.49

# Restart
docker-compose -f docker-compose.prod.yml up -d

# Verify old endpoint works
curl http://localhost:8000/profile/db-summary?user_email=leoklemet.pa@gmail.com
```

**Note**: Old component will still try to call `/api/metrics/profile/summary` but will fail gracefully.

---

## Monitoring

### Key Metrics

1. **Response Time**: Target < 500ms
   ```bash
   # Check p95 response time
   docker-compose logs api | grep "profile/summary" | awk '{print $NF}'
   ```

2. **Error Rate**: Target < 1%
   ```bash
   # Count errors
   docker-compose logs api | grep "profile/summary.*500" | wc -l
   ```

3. **Cache Hit Rate**: Target > 90% (after warmup)
   ```bash
   # Check cache logs
   docker-compose logs api | grep "cache_.*profile_summary"
   ```

### Alerts (TODO)

Set up alerts for:
- Response time > 1 second
- Error rate > 5% over 5 minutes
- Empty data for > 10 minutes (indicates pipeline failure)

---

## Common Questions

**Q: Why 60-second cache?**
A: Balance between freshness and BigQuery costs. Profile data doesn't change frequently.

**Q: Why top 3 only?**
A: Clean UI, fast queries. Future: Add "View All" drill-down.

**Q: What if BigQuery is down?**
A: Graceful degradation - empty arrays returned, UI shows "No data yet".

**Q: Can users customize time range?**
A: Not yet. Fixed to last 30 days. Future enhancement.

**Q: How accurate are interests?**
A: Basic keyword extraction. Will improve with dedicated mart table.

---

## Files Modified

**Backend**:
- `services/api/app/routers/metrics_profile.py` - Added `/summary` endpoint

**Frontend**:
- `apps/web/src/lib/api.ts` - Added `fetchProfileSummary()`
- `apps/web/src/components/profile/ProfileSummary.tsx` - Complete rewrite

**Tests**:
- `apps/web/tests/profile-warehouse.spec.ts` - New Playwright tests

**Documentation**:
- `docs/implementation/profile-warehouse-integration.md` - Full spec
- `runbooks/profile-warehouse.md` - This file

---

## Support

**Issue**: Profile page broken
**Contact**: Check logs first, then escalate
**Priority**: Medium (not critical path)

**SLA**:
- Response: 1 hour
- Resolution: 4 hours
