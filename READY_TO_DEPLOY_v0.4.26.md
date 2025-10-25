# 🚀 ApplyLens v0.4.26 - Ready to Deploy

## ✅ Pre-Deployment Complete

- ✅ Backend router created: `inbox_actions.py`
- ✅ Frontend component updated: `InboxWithActions.tsx`
- ✅ API helpers updated: `api.ts`
- ✅ Docker images built and pushed:
  - `leoklemet/applylens-api:v0.4.26`
  - `leoklemet/applylens-web:v0.4.26`
- ✅ `docker-compose.prod.yml` updated
- ✅ Code committed and pushed to GitHub
- ✅ Documentation created

## 🎯 Quick Deploy Commands

### On Production Server (applylens.app)

```bash
# 1. SSH to server
ssh root@applylens.app

# 2. Pull latest code
cd /root/ApplyLens
git pull origin demo

# 3. Pull images
docker compose -f docker-compose.prod.yml pull api web

# 4. Deploy
docker compose -f docker-compose.prod.yml up -d --force-recreate api web

# 5. Restart nginx
docker restart applylens-nginx-prod

# 6. Verify
docker ps | grep applylens
curl https://applylens.app/api/ready
```

## 📋 What's New in v0.4.26

### Backend Endpoints
- `GET /api/actions/inbox` - Fetch actionable emails
- `POST /api/actions/explain` - Explain categorization
- `POST /api/actions/mark_safe` - Lower risk score
- `POST /api/actions/mark_suspicious` - Raise risk score
- `POST /api/actions/archive` - Hide from inbox
- `POST /api/actions/unsubscribe` - Mark sender muted

### Frontend Features
- Real data from `/api/actions/inbox`
- Conditional action buttons based on `allowed_actions`
- Inline "Explain why" functionality
- Toast notifications
- Loading states per action
- Auto-refresh after actions

### Production Safety
- `ALLOW_ACTION_MUTATIONS` env var control
- Returns 403 in prod if mutations disabled
- Graceful ES fallback (returns empty array)
- User authentication required
- CSRF protection on all POST endpoints

## 🧪 Testing After Deployment

### 1. Check Actions Page
Visit: https://applylens.app/inbox-actions
- Should load without errors
- Should show actionable emails count
- Buttons should appear conditionally

### 2. Test Explain Button
- Click "Explain why" on any email
- Should show inline explanation

### 3. Test Mutations (if enabled)
- Try Archive, Safe, Suspicious, Unsub buttons
- In production: Should see "read-only" message unless `ALLOW_ACTION_MUTATIONS=true`

### 4. Check Logs
```bash
docker logs applylens-api-prod --tail 50
docker logs applylens-web-prod --tail 50
```

## 🔄 Rollback Plan (if needed)

```bash
cd /root/ApplyLens
# Edit docker-compose.prod.yml to use v0.4.25
sed -i 's/v0.4.26/v0.4.25/g' docker-compose.prod.yml
docker compose -f docker-compose.prod.yml pull api web
docker compose -f docker-compose.prod.yml up -d --force-recreate api web
docker restart applylens-nginx-prod
```

## 📚 Documentation Files
- `ACTIONS_IMPLEMENTATION.md` - Full implementation details
- `DEPLOYMENT_CHECKLIST_v0.4.26.md` - Complete deployment checklist
- `DEPLOY_v0.4.26.sh` - Automated deployment script

## 🎊 Next Steps After Deployment
1. Monitor logs for 10 minutes
2. Test Actions page functionality
3. Verify no errors in production
4. Consider enabling mutations: `ALLOW_ACTION_MUTATIONS=true`
5. Collect user feedback
6. Plan Playwright E2E tests

## 📞 Support
If issues occur:
- Check API logs: `docker logs applylens-api-prod --tail 200`
- Check Web logs: `docker logs applylens-web-prod --tail 50`
- Check nginx: `docker logs applylens-nginx-prod --tail 100`
- Verify ES: `curl http://localhost:9200/_cluster/health`
- Rollback if critical (use commands above)

---

**Ready to deploy!** All code is tested locally, images are pushed, and documentation is complete. 🚀
