# ✅ Docker Stack Setup Complete

## Current Status

All essential services are now running in Docker:

```
✅ Database (PostgreSQL 16)      → port 5433
✅ Elasticsearch 8.13.4          → port 9200
✅ API (FastAPI with uvicorn)    → port 8003
✅ Web (React + Vite)            → port 5175
✅ Ollama (LLM service)          → port 11434
✅ Kibana (optional)             → port 5601
✅ Prometheus (optional)         → port 9090
✅ Grafana (optional)            → port 3000
```

## ✅ What Works Now

1. **Database**: Fresh PostgreSQL instance with all migrations applied (up to 0033_sender_overrides)
2. **API Server**: Running on port 8003, health endpoints responding correctly
3. **Web Frontend**: Running on port 5175, Vite dev server active
4. **Smoke Tests**: 2/2 passing (healthz ✓, ready ✓)

## 🔧 What Was Fixed

1. **Database Credentials**: Reset database volume to match .env file (`postgres:postgres`)
2. **API Dependencies**: Rebuilt Docker image with latest code including `itsdangerous`
3. **Migrations**: Ran all 33 Alembic migrations successfully
4. **Port Configuration**: Aligned all services to use correct ports
5. **Test Tasks**: Updated VS Code tasks to point to correct endpoints

## ⚠️ Known Issues

### 1. Nginx Not Running
- **Issue**: Duplicate default server configuration for port 80
- **Impact**: No same-origin proxy, CORS issues for cross-port requests
- **Workaround**: Testing directly against API (8003) and web (5175) ports
- **Fix Needed**: Review `/etc/nginx/conf.d/` configs, remove duplicate `default_server` directives

### 2. CORS Configuration
- **Current**: API on 8003, Web on 5175 (different origins)
- **Issue**: Will cause cookie/auth problems for full E2E suite
- **Solution Options**:
  - **A) Fix Nginx** (recommended): Single origin with `/api` proxy
  - **B) API CORS headers**: Add `CORS_ALLOW_ORIGINS=http://localhost:5175` to API env

## 🎯 Next Steps

### Immediate (For Full E2E Suite)

1. **Fix Nginx Configuration**
   ```bash
   cd D:\ApplyLens\infra
   # Check which configs have duplicate default_server
   docker exec applylens-nginx ls -la /etc/nginx/conf.d/
   ```

2. **Enable Dev Routes on API**
   ```yaml
   # Add to docker-compose.yml under api.environment:
   ALLOW_DEV_ROUTES: "1"
   ```
   Then restart: `docker compose restart api`

3. **Update Test Configuration**
   ```typescript
   // For same-origin setup (after Nginx is fixed):
   E2E_BASE_URL=http://127.0.0.1
   E2E_API=http://127.0.0.1/api

   // For CORS setup (current):
   E2E_BASE_URL=http://127.0.0.1:5175
   E2E_API=http://127.0.0.1:8003
   ```

4. **Enable Authentication**
   ```json
   // Remove SKIP_AUTH=1 from tasks.json
   // Set USE_SMOKE_SETUP=true to enable seeding
   ```

### Future Improvements

1. **Test Segmentation**
   - Create separate Playwright projects for API vs UI tests
   - API tests: 6 workers (faster, no browser overhead)
   - UI tests: 4 workers (limited by Chromium instances)

2. **Preflight Checks**
   - Add `beforeAll()` hook to verify inbox has data
   - Fail fast if seed didn't work

3. **Better Debugging**
   - Add `--trace=retain-on-failure` to test runs
   - Configure `--retries=1` for flaky tests

## 📊 Test Results Summary

### Smoke Tests (Health Only)
```
✓ GET /healthz → {status: "ok"}
✓ GET /ready → {status: "ready", db: "ok", es: "ok"}
```
**Pass Rate**: 2/2 (100%)

### Full E2E Suite (Last Run)
```
✓ Passed: 10 tests (API-only, no auth required)
✗ Failed: 77 tests (need frontend + auth)
⊘ Skipped: 4 tests
```
**Pass Rate**: 10/87 (11.5%)
**Expected**: ~100% after Nginx + auth enabled

## 🚀 Running Tests

### Smoke Tests (No Auth)
```bash
cd D:\ApplyLens\apps\web
npm run test:smoke
```

### Full E2E Suite (Requires Auth + Seed)
```bash
# After fixing Nginx and enabling dev routes:
$env:USE_SMOKE_SETUP="true"
$env:SEED_COUNT="60"
npm run test:e2e -- --workers=8
```

### Individual Test File
```bash
npx playwright test tests/e2e-new/pipeline.spec.ts --headed
```

## 📝 Configuration Files

| File | Purpose | Status |
|------|---------|--------|
| `infra/.env` | Environment variables | ✅ Configured |
| `infra/docker-compose.yml` | Service orchestration | ✅ Working (except nginx) |
| `apps/web/playwright.config.ts` | Test framework config | ✅ Multi-env support |
| `apps/web/.vscode/tasks.json` | VS Code test tasks | ✅ 11 tasks defined |
| `services/api/alembic/versions/*` | Database migrations | ✅ All applied |

## 🔗 Service URLs

- **Web Frontend**: http://127.0.0.1:5175
- **API Server**: http://127.0.0.1:8003
- **API Health**: http://127.0.0.1:8003/healthz
- **API Ready**: http://127.0.0.1:8003/ready
- **Elasticsearch**: http://127.0.0.1:9200
- **Kibana**: http://127.0.0.1:5601
- **Grafana**: http://127.0.0.1:3000
- **Prometheus**: http://127.0.0.1:9090

## 🐛 Troubleshooting

### API Won't Start
```bash
docker logs infra-api-1 --tail 50
# Common issues:
# - Database password mismatch → reset db volume
# - Missing dependencies → rebuild image
# - Port conflict → stop other containers
```

### Database Connection Errors
```bash
docker exec infra-db-1 psql -U postgres -d applylens -c "\dt"
# Should show 27 tables
```

### Tests Failing
```bash
# Check services are healthy
docker compose ps

# Verify API endpoints
curl http://127.0.0.1:8003/healthz
curl http://127.0.0.1:8003/ready

# Check test configuration
cat apps/web/playwright.config.ts | grep BASE_URL
```

## 📚 Resources

- **Playwright Docs**: https://playwright.dev/docs/intro
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Alembic Docs**: https://alembic.sqlalchemy.org/
- **Docker Compose**: https://docs.docker.com/compose/

---

**Last Updated**: 2025-10-30
**Smoke Tests**: ✅ Passing (2/2)
**Full E2E**: ⚠️ Partial (10/87) - Need auth + Nginx
**Stack Status**: 🟢 API + DB + ES + Web Running
