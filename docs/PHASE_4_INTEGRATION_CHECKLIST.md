# Phase 4 Integration Checklist

## ✅ Completed Steps

1. ✅ Created action models (ActionType, ProposedAction, AuditAction, Policy) in `models.py`
2. ✅ Created Alembic migration `0016_phase4_actions.py`
3. ✅ Implemented Yardstick policy engine in `core/yardstick.py`
4. ✅ Implemented action executors in `core/executors.py`
5. ✅ Created actions router in `routers/actions.py`
6. ✅ Created default policy seeds in `seeds/policies.py`
7. ✅ Created frontend API client in `lib/actionsClient.ts`
8. ✅ Created ActionsTray component in `components/ActionsTray.tsx`
9. ✅ Integrated ActionsTray in AppHeader with badge
10. ✅ Registered actions router in `main.py`
11. ✅ Installed html2canvas package

## 🔄 Next Steps (Requires Docker Running)

### 1. Start Docker Services

```powershell
cd d:/ApplyLens/infra
docker compose up -d
```

### 2. Apply Database Migration

```powershell
docker exec infra-api-1 alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade 0015 -> 0016, phase4 actions
```

### 3. Seed Default Policies

```powershell
docker exec infra-api-1 python -c "
from app.db import SessionLocal
from app.seeds.policies import seed_policies

db = SessionLocal()
try:
    count = seed_policies(db)
    print(f'Seeded {count} policies')
finally:
    db.close()
"
```

Or using the module runner:
```powershell
docker exec infra-api-1 python -m app.seeds.policies
```

### 4. Verify API Endpoints

```powershell
# List policies
curl http://localhost:8003/api/actions/policies | jq .

# Expected output: Array of 5 default policies
```

### 5. Test Propose Actions

```powershell
# Propose actions for recent emails
curl -X POST http://localhost:8003/api/actions/propose `
  -H "Content-Type: application/json" `
  -d '{"limit":20}' | jq .

# Expected output: {"created": [1, 2, 3], "count": 3}
```

### 6. Test Tray Endpoint

```powershell
# List pending actions
curl http://localhost:8003/api/actions/tray | jq .

# Expected output: Array of pending actions with email details
```

### 7. Test Frontend (Manual)

1. Start the web app:
   ```powershell
   cd d:/ApplyLens/apps/web
   npm run dev
   ```

2. Open browser to http://localhost:5175

3. Click the "Actions" button in the header (with Sparkles icon)

4. Verify:
   - Tray slides in from right
   - Pending actions are displayed
   - Can expand "Explain" section
   - Can click Approve/Reject buttons
   - Screenshot is captured on approve
   - Action is removed from tray after approve/reject

## 🧪 Testing Actions Flow

### Manual Test Workflow

1. **Create test emails with various categories:**
   - High-risk emails (risk_score >= 80) → Should trigger quarantine
   - Promotions with expires_at in past → Should trigger archive
   - Application emails with job keywords → Should trigger label

2. **Propose actions:**
   ```powershell
   curl -X POST http://localhost:8003/api/actions/propose -d '{"limit":50}'
   ```

3. **View pending in UI:**
   - Open tray, verify actions appear
   - Check confidence percentages
   - Expand rationale, verify narratives

4. **Approve an action:**
   - Click "Approve" button
   - Verify screenshot capture (check browser console)
   - Verify toast notification
   - Verify action removed from tray

5. **Check audit trail:**
   ```powershell
   docker exec -it infra-db-1 psql -U postgres -d lens -c "
   SELECT id, email_id, action, outcome, actor, created_at 
   FROM audit_actions 
   ORDER BY created_at DESC 
   LIMIT 10;"
   ```

6. **Verify screenshot saved:**
   ```powershell
   docker exec infra-api-1 ls -lh /data/audit/2025-10/
   ```

## 📊 Monitoring

### Check Prometheus Metrics (Future)

Once metrics are added:
```powershell
curl http://localhost:8003/metrics | grep actions
```

Expected metrics:
- `actions_proposed_total{policy="..."}`
- `actions_executed_total{action="...", outcome="..."}`
- `actions_failed_total{action="...", error_type="..."}`

## 🐛 Troubleshooting

### Migration Fails

```powershell
# Check current migration version
docker exec infra-api-1 alembic current

# Check migration history
docker exec infra-api-1 alembic history

# If stuck, downgrade and retry
docker exec infra-api-1 alembic downgrade -1
docker exec infra-api-1 alembic upgrade head
```

### Seeds Fail

```powershell
# Check if policies table exists
docker exec -it infra-db-1 psql -U postgres -d lens -c "\d policies"

# Check existing policies
docker exec -it infra-db-1 psql -U postgres -d lens -c "SELECT * FROM policies;"

# Reset policies (WARNING: Deletes all)
docker exec infra-api-1 python -c "
from app.db import SessionLocal
from app.seeds.policies import reset_policies

db = SessionLocal()
try:
    reset_policies(db)
    print('Policies reset')
finally:
    db.close()
"
```

### API Returns 500

```powershell
# Check API logs
docker logs infra-api-1 --tail 50

# Check for import errors
docker exec infra-api-1 python -c "from app.routers import actions; print('OK')"

# Check for Yardstick errors
docker exec infra-api-1 python -c "
from app.core.yardstick import evaluate_policy
policy = {'condition': {'eq': ['category', 'promotions']}}
ctx = {'category': 'promotions'}
print(evaluate_policy(policy, ctx))
"
```

### Frontend Tray Not Loading

1. Check browser console for errors
2. Verify API endpoint is accessible:
   ```powershell
   curl http://localhost:8003/api/actions/tray
   ```
3. Check CORS headers:
   ```powershell
   curl -i -H "Origin: http://localhost:5175" http://localhost:8003/api/actions/tray
   ```

### Screenshot Capture Fails

1. Check browser console for html2canvas errors
2. Verify package is installed:
   ```powershell
   cd d:/ApplyLens/apps/web
   npm list html2canvas
   ```
3. Screenshot failure is non-blocking - action will still execute

## 📝 Remaining Work

### Backend
- [ ] Integrate executors with Gmail/Calendar/Tasks services
- [ ] Add ES aggregations to rationale builder
- [ ] Implement KNN neighbors in rationale
- [ ] Add SSE events endpoint
- [ ] Add Prometheus metrics counters
- [ ] Write unit tests (Yardstick, propose, approve)

### Frontend
- [ ] Add "Always do this" button (policy creation)
- [ ] Add policy management UI (CRUD)
- [ ] Add policy testing UI
- [ ] Add real-time SSE updates
- [ ] Write Playwright E2E tests

### Infrastructure
- [ ] Screenshot cleanup job (delete > 90 days)
- [ ] Audit log retention policy
- [ ] Rate limiting on policy creation
- [ ] Documentation (PHASE_4_ACTIONS.md)

## 🎉 Success Criteria

Phase 4 is complete when:

✅ Migration applied successfully
✅ Default policies seeded
✅ Actions router responds to all endpoints
✅ Frontend tray displays pending actions
✅ Approve button executes action and saves audit
✅ Reject button dismisses action and audits as noop
✅ Screenshot captured and saved on approve
✅ Badge shows pending count in header
✅ Rationale displays in expandable section

Current Status: **85% Complete** (Core functionality done, integration + testing pending)
