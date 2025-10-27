# Production Status - October 26, 2025

## Current Deployment

**Date:** October 26, 2025
**Branch:** demo
**Status:** ✅ All systems operational

## Container Versions

| Service | Version | Status | Uptime |
|---------|---------|--------|--------|
| Web (Frontend) | v0.4.55 | ✅ Healthy | 15 minutes |
| API (Backend) | v0.4.51 | ✅ Running | 2 hours |
| Nginx (Proxy) | 1.27-alpine | ✅ Healthy | 2 hours |
| PostgreSQL | 16-alpine | ✅ Healthy | 3 hours |
| Elasticsearch | 8.13.4 | ✅ Healthy | 3 hours |
| Kibana | 8.13.4 | ✅ Healthy | 3 hours |
| Redis | 7-alpine | ✅ Healthy | 3 hours |
| Prometheus | v2.55.1 | ✅ Healthy | 3 hours |
| Grafana | 11.1.0 | ✅ Healthy | 3 hours |
| Cloudflared | latest | ✅ Running | 3 hours |

## Recent Deployments

### v0.4.55 - Settings Account Card Polish (Current)
**Deployed:** October 26, 2025
**Commit:** 2ccc405

**Changes:**
- Refined Settings page Account card styling
- Improved text contrast (zinc-300 and white colors)
- Better visual hierarchy with gap-3 spacing
- Enhanced readability in dark mode

**Files Modified:**
- `apps/web/src/pages/Settings.tsx`

**Documentation:**
- `SETTINGS_POLISH_v0.4.55.md`
- `docs/ACTIONS_BADGE_SYSTEM.md`

### v0.4.54 - Settings Account Icon
**Deployed:** October 26, 2025
**Commit:** 2187028

**Changes:**
- Added circular user icon avatar to Account card
- Two-line layout: "Signed in as" + email
- Responsive layout (mobile stacked, desktop side-by-side)
- Email wrapping for long addresses

### v0.4.53 - Logout Cache Clear
**Deployed:** October 26, 2025
**Commit:** 027c533

**Changes:**
- Added clearCurrentUser() function to auth.ts
- Clear cached user data on logout to prevent stale UI flash
- Updated logoutUser() to call clearCurrentUser() before redirect
- Improved logout UX

### v0.4.52 - Settings Page Enhancement
**Deployed:** October 26, 2025

**Changes:**
- Added Account card to Settings page
- Logout button with data-testid="logout-button"
- Created settings-logout.spec.ts tests
- Added [prodSafe] test suite

### v0.4.51 - Profile Warehouse Integration
**Deployed:** Earlier

**Changes:**
- Added last_sync_at field from BigQuery
- Added dataset field for debugging
- Defensive rendering for sync status
- Profile page warehouse metrics

## Feature Highlights

### Settings Page ✅
- **Account Card:** User icon avatar + email display
- **Logout:** Clear cache on logout, redirect to home
- **Search Scoring:** Recency scale configuration (3d/7d/14d)
- **Experimental Badge:** On Search Scoring card

### Actions System ✅
- **Badge Count:** Unified between navbar and tray
- **Side Drawer:** ActionsTray with approve/reject functionality
- **Polling:** Auto-refresh every 30 seconds
- **Real-time Updates:** Local state updates on approve/reject

### Profile Page ✅
- **Warehouse Metrics:** Last sync timestamp
- **Dataset Display:** Debug information
- **Defensive Rendering:** Graceful handling of no data

### Authentication ✅
- **Cache Management:** In-memory user cache
- **Logout Flow:** Clear cache → redirect → clean UI
- **getCurrentUser():** Cached API calls

## Git Status

```
Branch: demo
Status: Up to date with origin/demo
Working tree: Clean (no uncommitted changes)
```

## Recent Commits (Last 10)

1. `79c9655` - Add documentation for unified Actions badge count system
2. `2ccc405` - Deploy v0.4.55: Settings Account card styling polish
3. `c784bc5` - v0.4.55: Polish Settings Account card styling for better contrast
4. `ab16c6b` - Add documentation for Settings Account card enhancement v0.4.54
5. `2187028` - v0.4.54: Settings Account card with user icon avatar
6. `0a902d7` - Add account icon to Settings page Account card
7. `027c533` - v0.4.53: Clear cached user on logout to prevent stale UI flash
8. `f5b7bd8` - Add deployment documentation for Settings page v0.4.52
9. `7c50174` - Settings page: Add Account card with logout functionality
10. `dd6e832` - Profile feature: Add warehouse sync debug fields and polish UX (v0.4.51)

## Docker Images

### Web (Frontend)
```bash
leoklemet/applylens-web:v0.4.55
```

**Build Command:**
```bash
cd d:\ApplyLens\apps\web
docker build -f Dockerfile.prod -t leoklemet/applylens-web:v0.4.55 .
docker push leoklemet/applylens-web:v0.4.55
```

### API (Backend)
```bash
leoklemet/applylens-api:v0.4.51
```

**Build Command:**
```bash
cd d:\ApplyLens\services\api
docker build -f Dockerfile.prod -t leoklemet/applylens-api:v0.4.51 .
docker push leoklemet/applylens-api:v0.4.51
```

## Deployment Commands

### Deploy Specific Service
```bash
cd d:\ApplyLens
docker-compose -f docker-compose.prod.yml up -d web
docker-compose -f docker-compose.prod.yml up -d api
```

### Deploy All Services
```bash
cd d:\ApplyLens
docker-compose -f docker-compose.prod.yml up -d
```

### Check Container Status
```bash
docker ps --filter "name=applylens"
```

### View Logs
```bash
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f api
```

## Health Checks

### Frontend (Web)
- URL: http://localhost:5175
- Health: ✅ Serving static files via Nginx
- Status: Up 15 minutes, healthy

### Backend (API)
- URL: http://localhost:8003
- Health: ✅ Running FastAPI application
- Status: Up 2 hours

### Database (PostgreSQL)
- Port: 5432 (internal)
- Health: ✅ pg_isready check passing
- Status: Up 3 hours, healthy

### Search (Elasticsearch)
- Port: 9200 (internal)
- Health: ✅ Cluster health check passing
- Status: Up 3 hours, healthy

### Cache (Redis)
- Port: 6379 (internal)
- Health: ✅ Ping check passing
- Status: Up 3 hours, healthy

## Testing Status

### E2E Tests
- **Location:** `apps/web/tests/`
- **Framework:** Playwright
- **Coverage:** Settings logout flow, Profile page, Actions tray

### Test Suites
- ✅ `settings-logout.spec.ts` - [prodSafe]
- ✅ `profile-warehouse.spec.ts` - Warehouse metrics
- ✅ Other E2E tests as configured

### Run Tests
```bash
cd d:\ApplyLens\apps\web
$env:SKIP_AUTH='1'
npx playwright test settings-logout --reporter=line
```

## Documentation

### Project Documentation
- `SETTINGS_ACCOUNT_ICON_v0.4.54.md` - Account icon implementation
- `SETTINGS_POLISH_v0.4.55.md` - Styling refinements
- `SETTINGS_LOGOUT_v0.4.52.md` - Logout functionality
- `docs/ACTIONS_BADGE_SYSTEM.md` - Badge count architecture

### API Documentation
- FastAPI auto-docs: http://localhost:8003/docs
- Redoc: http://localhost:8003/redoc

## Monitoring

### Prometheus
- URL: http://localhost:9090
- Status: ✅ Collecting metrics
- Scrape interval: 15s

### Grafana
- URL: http://localhost:3000
- Status: ✅ Dashboards available
- Default credentials: admin/admin

### Kibana
- URL: http://localhost:5601/kibana/
- Status: ✅ Connected to Elasticsearch
- Index: `gmail_emails`

## Network

### External Access
- Cloudflare Tunnel: ✅ Active
- Domain: applylens.app
- SSL: Managed by Cloudflare

### Internal Services
- Network: applylens-prod (172.25.0.0/16)
- DNS: Container name resolution
- Inter-service communication: ✅ Healthy

## Volumes

### Persistent Data
- `db_data_prod` - PostgreSQL database
- `es_data_prod` - Elasticsearch indices
- `redis_data_prod` - Redis cache
- `prometheus_data_prod` - Metrics data
- `grafana_data_prod` - Dashboard configs
- `kibana_data_prod` - Kibana state

### Logs
- `api_logs_prod` - API application logs
- `nginx_logs_prod` - Access and error logs

## Environment

### Configuration
- File: `infra/.env`
- Secrets: `infra/secrets/` (git-ignored)
- BigQuery: Service account key in `secrets/`

### Feature Flags
- `CHAT_STREAMING_ENABLED=true` - SSE streaming for chat
- `ALLOW_ACTION_MUTATIONS=true` - Actions lifecycle management
- `USE_WAREHOUSE_METRICS=0` - BigQuery integration (disabled by default)

## Next Steps

### Planned Features
1. Real-time Actions updates (WebSocket)
2. Aggregate action summaries
3. Enhanced monitoring dashboards
4. Additional Settings page features

### Maintenance
- Monitor container health
- Review logs for errors
- Update dependencies as needed
- Backup database regularly

## Support

### Logs Location
- API: `docker-compose logs -f api`
- Web: `docker-compose logs -f web`
- Nginx: `docker-compose logs -f nginx`

### Restart Services
```bash
docker-compose -f docker-compose.prod.yml restart web
docker-compose -f docker-compose.prod.yml restart api
```

### Emergency Rollback
```bash
# Rollback web to previous version
docker-compose -f docker-compose.prod.yml pull web:v0.4.54
# Update docker-compose.prod.yml
# Redeploy
docker-compose -f docker-compose.prod.yml up -d web
```

---

**Last Updated:** October 26, 2025
**Updated By:** Copilot
**Status:** ✅ All systems operational, production ready
