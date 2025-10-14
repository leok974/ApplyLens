# Post-Deployment Verification Checklist

Use this checklist after deploying ApplyLens to production to verify everything is working correctly.

## Automated Checks

Run the health check script first:

```bash
./health-check.sh
```

✅ All services should report healthy before proceeding with manual checks.

---

## Manual Verification (30 minutes)

### 1. Infrastructure Health ✓

- [ ] **All Docker containers running**
  ```bash
  docker compose -f docker-compose.prod.yml ps
  ```
  Expected: 9 services in "running" state (or 10 with cloudflared)

- [ ] **No recent errors in logs**
  ```bash
  docker compose -f docker-compose.prod.yml logs --tail=100 | grep -i error
  ```
  Expected: No critical errors (some warnings are normal)

- [ ] **Database connectivity**
  ```bash
  docker compose -f docker-compose.prod.yml exec db pg_isready
  ```
  Expected: "accepting connections"

- [ ] **Elasticsearch cluster health**
  ```bash
  curl -X GET "http://localhost:9200/_cluster/health?pretty"
  ```
  Expected: `"status": "green"` or `"yellow"` (yellow is acceptable for single-node)

### 2. External Access via Cloudflare ✓

- [ ] **Main domain loads**
  - Visit: https://applylens.app/
  - Expected: API response or redirect to /web/

- [ ] **Frontend accessible**
  - Visit: https://applylens.app/web/
  - Expected: React app loads, no console errors

- [ ] **API docs accessible**
  - Visit: https://applylens.app/docs/
  - Expected: Swagger/OpenAPI documentation

- [ ] **Cloudflare headers present**
  ```bash
  curl -I https://applylens.app/ | grep -i "cf-ray"
  ```
  Expected: `cf-ray` header present (confirms Cloudflare routing)

- [ ] **HTTPS enforced**
  ```bash
  curl -I http://applylens.app/
  ```
  Expected: 301/302 redirect to HTTPS

### 3. Frontend Functionality ✓

Open https://applylens.app/web/ in browser and verify:

- [ ] **Page loads without errors**
  - Check browser console (F12) for JavaScript errors
  - Check network tab for failed requests

- [ ] **Assets load correctly**
  - Images display
  - Fonts render properly
  - CSS styles applied

- [ ] **Navigation works**
  - Click through main navigation
  - Test routing (if multi-page SPA)

- [ ] **API connectivity from frontend**
  - Open browser console
  - Check XHR/Fetch requests in Network tab
  - Verify requests go to https://applylens.app/ (not localhost)

### 4. API Functionality ✓

Test API endpoints:

- [ ] **Health endpoint**
  ```bash
  curl https://applylens.app/health
  ```
  Expected: `{"status": "healthy"}` or similar

- [ ] **API root endpoint**
  ```bash
  curl https://applylens.app/
  ```
  Expected: API welcome message or redirect

- [ ] **OpenAPI docs endpoint**
  ```bash
  curl -I https://applylens.app/docs/
  ```
  Expected: HTTP 200

- [ ] **Authentication endpoints available**
  ```bash
  curl -I https://applylens.app/auth/google/
  ```
  Expected: HTTP 302 (redirect to Google OAuth) or 200

### 5. OAuth Authentication Flow ✓

**CRITICAL:** Test the full OAuth flow

- [ ] **Google OAuth configured**
  - Go to: https://console.cloud.google.com/apis/credentials
  - Verify redirect URI: `https://applylens.app/auth/google/callback`
  - Verify JS origin: `https://applylens.app`

- [ ] **Login flow works**
  1. Visit https://applylens.app/web/
  2. Click "Sign in with Google" (or similar)
  3. Redirected to Google OAuth consent screen
  4. After granting permission, redirected back to applylens.app
  5. User logged in successfully

- [ ] **Session persistence**
  - Refresh page
  - User stays logged in

- [ ] **Logout works**
  - Click logout
  - Session cleared
  - Can log in again

### 6. Database Operations ✓

- [ ] **Migrations applied**
  ```bash
  docker compose -f docker-compose.prod.yml exec api alembic current
  ```
  Expected: Shows current migration version (head)

- [ ] **Data persists**
  - Create test data via API or frontend
  - Restart containers:
    ```bash
    docker compose -f docker-compose.prod.yml restart api
    ```
  - Verify data still exists

- [ ] **Database backups configured** (if automated)
  ```bash
  ls -lh /path/to/backups/
  ```
  Expected: Recent backup files

### 7. Monitoring & Observability ✓

- [ ] **Grafana accessible**
  - Visit: https://applylens.app/grafana/
  - Expected: Login page or dashboards
  - Test login with credentials from `.env.prod`

- [ ] **Prometheus accessible**
  - Visit: https://applylens.app/prometheus/
  - Expected: Prometheus UI
  - Check targets: https://applylens.app/prometheus/targets
  - Verify API target is UP

- [ ] **Kibana accessible**
  - Visit: https://applylens.app/kibana/
  - Expected: Kibana UI
  - Verify Elasticsearch connection

- [ ] **Metrics being collected**
  - Grafana: Check dashboards for data
  - Prometheus: Run sample query: `up{job="api"}`
  - Expected: Data points visible

### 8. Performance & Load ✓

- [ ] **Page load time acceptable**
  - Frontend loads in < 3 seconds
  - API responses < 500ms for simple endpoints

- [ ] **No memory leaks**
  ```bash
  docker stats --no-stream
  ```
  Expected: Memory usage stable, not constantly increasing

- [ ] **API rate limits work** (if configured)
  ```bash
  # Make rapid requests
  for i in {1..20}; do curl https://applylens.app/health; done
  ```
  Expected: Rate limiting triggers if configured (429 status)

### 9. Security Checks ✓

- [ ] **Security headers present**
  ```bash
  curl -I https://applylens.app/ | grep -E "(X-Frame-Options|X-Content-Type-Options|X-XSS-Protection|Strict-Transport-Security)"
  ```
  Expected: Security headers configured

- [ ] **No sensitive data exposed**
  - Check API responses for secrets
  - Check frontend source for hardcoded credentials
  - Verify `.env.prod` not accessible: https://applylens.app/.env.prod
  - Expected: 404 or 403

- [ ] **Monitoring tools protected**
  - Try accessing without auth: https://applylens.app/grafana/
  - Expected: Basic auth prompt or login required

- [ ] **CORS configured correctly**
  ```bash
  curl -H "Origin: https://malicious-site.com" -I https://applylens.app/
  ```
  Expected: No `Access-Control-Allow-Origin: *` (should be specific)

### 10. Error Handling ✓

- [ ] **404 pages work**
  - Visit: https://applylens.app/nonexistent-page
  - Expected: Custom 404 or API error response

- [ ] **500 errors logged**
  - Trigger error (if test endpoint exists)
  - Check logs:
    ```bash
    docker compose -f docker-compose.prod.yml logs api --tail=50
    ```
  - Expected: Error logged with stack trace

- [ ] **Frontend error boundaries**
  - Trigger JavaScript error (if test available)
  - Expected: Graceful error message, not white screen

### 11. Disaster Recovery ✓

- [ ] **Backup script works**
  ```bash
  # If automated backup exists
  ./backup-database.sh
  ```
  Expected: Backup created successfully

- [ ] **Rollback script available**
  ```bash
  ./rollback.sh
  ```
  Expected: Menu with rollback options

- [ ] **Logs accessible**
  ```bash
  docker compose -f docker-compose.prod.yml logs --tail=100
  ```
  Expected: Recent logs from all services

---

## Final Verification Summary

Once all checks pass, run comprehensive verification:

```bash
# Run health check
./health-check.sh

# Check external access
curl -I https://applylens.app/
curl -I https://applylens.app/web/
curl -I https://applylens.app/docs/

# Verify Cloudflare routing
curl -I https://applylens.app/ | grep cf-ray

# Check service status
docker compose -f docker-compose.prod.yml ps
```

### Success Criteria

✅ All automated health checks pass  
✅ Frontend loads and renders correctly  
✅ API responds to requests  
✅ OAuth login flow completes successfully  
✅ Database operations work  
✅ Monitoring dashboards accessible  
✅ Security headers configured  
✅ Cloudflare routing confirmed (cf-ray header)  

### Known Issues to Monitor

Document any expected issues or temporary workarounds:

- [ ] _Add any known issues here_
- [ ] _Add temporary fixes or workarounds_

---

## Post-Deployment Tasks

After verification passes:

### Immediate (Day 1)

- [ ] Update Google OAuth production settings
- [ ] Configure monitoring alerts (email/Slack)
- [ ] Set up automated database backups (cron)
- [ ] Update documentation with production URLs
- [ ] Notify team deployment is complete

### Short-term (Week 1)

- [ ] Monitor error rates and performance
- [ ] Review logs for issues
- [ ] Configure Cloudflare firewall rules
- [ ] Set up rate limiting (if not done)
- [ ] Create runbooks for common issues
- [ ] Test disaster recovery procedures

### Ongoing

- [ ] Weekly backup verification
- [ ] Monthly dependency updates
- [ ] Quarterly disaster recovery drills
- [ ] Review monitoring dashboards
- [ ] Performance optimization

---

## Troubleshooting Common Issues

### Deployment succeeded but site not accessible

1. Check Cloudflare Tunnel status
2. Verify DNS records in Cloudflare dashboard
3. Check nginx logs for errors
4. Verify firewall rules on server

### OAuth redirects to localhost

1. Update `.env.prod`: `API_URL=https://applylens.app`
2. Update Google OAuth redirect URI
3. Rebuild and redeploy: `./deploy-to-server.sh`

### Frontend loads but API requests fail

1. Check browser console network tab
2. Verify CORS settings in API
3. Check nginx reverse proxy configuration
4. Verify API_URL in frontend environment

### 502 Bad Gateway

1. Check nginx status: `docker compose ps nginx`
2. Check API status: `docker compose ps api`
3. Check logs: `docker compose logs nginx api --tail=100`
4. Restart services: `./rollback.sh` → Option 1 (Quick Restart)

---

## Contact & Support

**Documentation:**
- Main: `PRODUCTION_DOMAIN_SETUP.md`
- Cloudflare: `CLOUDFLARE_TUNNEL_SETUP.md`
- Quick Reference: `PROD_DOMAIN_QUICK_REF.md`

**Scripts:**
- Deploy: `./deploy-to-server.sh`
- Health Check: `./health-check.sh`
- Rollback: `./rollback.sh`

**Emergency Rollback:**
```bash
./rollback.sh
# Select Option 4: Roll back to previous commit
```

---

**Deployment Date:** _____________  
**Deployed By:** _____________  
**Verification Completed By:** _____________  
**Issues Found:** _____________  
**Sign-off:** _____________
