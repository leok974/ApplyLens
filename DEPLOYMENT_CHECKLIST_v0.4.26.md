# Deployment Checklist - v0.4.26 Actions Page

## Pre-Deployment ✅

- [x] Built API Docker image: `leoklemet/applylens-api:v0.4.26`
- [x] Pushed API image to Docker Hub
- [x] Built Web Docker image: `leoklemet/applylens-web:v0.4.26`
- [x] Pushed Web image to Docker Hub
- [x] Updated `docker-compose.prod.yml` with v0.4.26 tags
- [x] Created deployment script: `DEPLOY_v0.4.26.sh`

# Deployment Checklist - v0.4.26 Actions Page

## Pre-Deployment ✅

- [x] Built API Docker image: `leoklemet/applylens-api:v0.4.26`
- [x] Pushed API image to Docker Hub
- [x] Built Web Docker image: `leoklemet/applylens-web:v0.4.26`
- [x] Pushed Web image to Docker Hub
- [x] Updated `docker-compose.prod.yml` with v0.4.26 tags
- [x] Created deployment script: `DEPLOY_v0.4.26.sh`

## Deployment Steps

**IMPORTANT**: This deployment assumes you're running on the production host that already has `docker-compose.prod.yml`. We do NOT use SSH to a public hostname or run `git pull` as part of deployment.

### On the production host where docker-compose.prod.yml exists:

```bash
# 1. Pull latest images
docker compose -f docker-compose.prod.yml pull api web

# 2. Recreate containers with new versions
docker compose -f docker-compose.prod.yml up -d --force-recreate api web

# 3. Restart nginx to clear DNS cache
docker restart applylens-nginx-prod

# 4. Verify health
curl https://applylens.app/api/healthz

# 5. Visit Actions page in browser
# https://applylens.app/web/inbox-actions
```

**Success Criteria**: If Actions page shows only "Explain why" button and no 403 errors, deploy is good.

### Alternative: Use the deployment script

```bash
./DEPLOY_v0.4.26.sh
```

## Post-Deployment Testing

### 1. Test Actions Inbox Endpoint
```bash
# Should return actionable emails (or empty array if none)
curl -H "Authorization: Bearer YOUR_TOKEN" https://applylens.app/api/actions/inbox
```

### 2. Test Actions Page in Browser
- Visit: https://applylens.app/inbox-actions
- Should load without errors
- Should show "N actionable emails" (or "0 actionable emails")
- Click "Explain why" button - should show explanation
- Action buttons should be visible only if allowed

### 3. Test Explain Endpoint
```bash
curl -X POST https://applylens.app/api/actions/explain \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message_id": "SOME_MESSAGE_ID"}'
```

### 4. Test Action Mutations (if enabled)
```bash
# Mark Safe
curl -X POST https://applylens.app/api/actions/mark_safe \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message_id": "SOME_MESSAGE_ID"}'

# Expected in production (if ALLOW_ACTION_MUTATIONS=false):
# {"detail": "Actions are read-only in production"}
```

### 5. Check for Errors
```bash
# API logs
docker logs applylens-api-prod --tail 100 | grep -i error

# Web logs
docker logs applylens-web-prod --tail 100 | grep -i error

# Nginx logs
docker logs applylens-nginx-prod --tail 100 | grep -i error
```

## Feature Verification

### Backend Endpoints
- [ ] `GET /api/actions/inbox` - Returns actionable emails
- [ ] `POST /api/actions/explain` - Returns explanation
- [ ] `POST /api/actions/mark_safe` - Updates email (or 403 if read-only)
- [ ] `POST /api/actions/mark_suspicious` - Updates email (or 403 if read-only)
- [ ] `POST /api/actions/archive` - Updates email (or 403 if read-only)
- [ ] `POST /api/actions/unsubscribe` - Updates email (or 403 if read-only)

### Frontend Features
- [ ] Actions page loads at `/inbox-actions`
- [ ] Shows count of actionable emails
- [ ] Displays emails in table format
- [ ] Shows reason/category for each email
- [ ] Risk scores displayed for high-risk emails
- [ ] "Explain why" button works
- [ ] Explanation shows inline after clicking
- [ ] Action buttons conditionally rendered based on `allowed_actions`
- [ ] Loading states during actions
- [ ] Success/error toast notifications
- [ ] Auto-refresh after successful action
- [ ] Clean empty state when no emails

## Production Safety Checks

- [ ] Elasticsearch gracefully handled if unavailable
- [ ] Returns empty array instead of crashing on ES errors
- [ ] User authentication enforced on all endpoints
- [ ] CSRF protection active on POST endpoints
- [ ] `ALLOW_ACTION_MUTATIONS` env var respected
- [ ] Read-only mode shows appropriate message
- [ ] No sensitive data exposed in error messages

## Monitoring

### Metrics to Watch
```bash
# Check Prometheus metrics
curl https://applylens.app/metrics | grep actions_

# Check API response times
# Check error rates
# Monitor ES query performance
```

### Logs to Monitor
```bash
# Follow API logs for 1 minute
timeout 60 docker logs applylens-api-prod -f | grep actions

# Check for any exceptions
docker logs applylens-api-prod --since 5m | grep -i exception
```

## Rollback Plan (if needed)

### Quick Rollback to v0.4.25
```bash
cd /root/ApplyLens

# Edit docker-compose.prod.yml
sed -i 's/v0.4.26/v0.4.25/g' docker-compose.prod.yml

# Redeploy previous version
docker compose -f docker-compose.prod.yml pull api web
docker compose -f docker-compose.prod.yml up -d --force-recreate api web
docker restart applylens-nginx-prod
```

## Environment Variables (Optional)

If you want to enable action mutations in production:

```bash
# Add to infra/.env
ALLOW_ACTION_MUTATIONS=true
```

Then restart:
```bash
docker compose -f docker-compose.prod.yml restart api
```

## Success Criteria

- ✅ No 500 errors in logs
- ✅ Actions page loads successfully
- ✅ Inbox endpoint returns data (or gracefully handles no data)
- ✅ Explain functionality works
- ✅ Action buttons behave correctly (work or show 403)
- ✅ No regression in existing features (Search, Tracker, etc.)
- ✅ Nginx routing works correctly
- ✅ All containers healthy

## Known Limitations

1. **Elasticsearch Required**: If ES is down, inbox returns empty array
2. **No Gmail Sync**: Actions only modify local ES index
3. **Unsubscribe is Passive**: Doesn't click unsubscribe links yet
4. **No Bulk Actions**: One email at a time
5. **Read-Only in Production**: Until `ALLOW_ACTION_MUTATIONS=true`

## Next Steps After Deployment

1. Monitor for 24 hours
2. Collect user feedback
3. Enable mutations if safe (`ALLOW_ACTION_MUTATIONS=true`)
4. Implement Playwright E2E tests
5. Consider bulk actions feature
6. Add action history/audit log view

## Support

If issues occur:
1. Check logs: `docker logs applylens-api-prod --tail 200`
2. Check nginx: `docker logs applylens-nginx-prod --tail 100`
3. Verify ES: `curl http://localhost:9200/_cluster/health`
4. Rollback if critical: Use rollback steps above

## Documentation

- Implementation details: `ACTIONS_IMPLEMENTATION.md`
- API documentation: Auto-generated at `/docs` endpoint
- Frontend code: `apps/web/src/components/InboxWithActions.tsx`
- Backend code: `services/api/app/routers/inbox_actions.py`
