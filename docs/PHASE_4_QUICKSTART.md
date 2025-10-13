# Phase 4 Enhancements - Quick Start Guide

**Last Updated:** January 12, 2025  
**Status:** ✅ Ready for use

---

## What's New?

### 1. "Always do this" Button ✨

- **What:** Creates learned policies from approved actions
- **How:** Click purple "Always do this" button in Actions Tray
- **Why:** Automate repetitive decisions (e.g., "always archive promos from this sender")

### 2. Prometheus Metrics 📊

- **What:** Track action proposals, executions, failures
- **Where:** <http://localhost:8003/metrics>
- **Why:** Monitor system health, alert on failures

### 3. Enhanced UI

- **What:** Improved ActionsTray with 3 action buttons
- **Buttons:** Approve (green), Reject (gray), Always (purple)
- **Features:** Success toasts, error handling, loading states

---

## Quick Test (Manual)

### Prerequisites

```powershell
# 1. Start Docker services
cd d:/ApplyLens/infra
docker compose up -d

# 2. Start frontend
cd d:/ApplyLens/apps/web
npm run dev

# 3. Open browser
# http://localhost:5175
```text

### Test Flow

**Step 1: Sync Emails**

```bash
# Via UI: Click "Sync Now" button
# Or via API:
curl -X POST http://localhost:8003/api/gmail/sync
```text

**Step 2: Create Test Policy (That Will Match)**

Let's create a policy that will match all emails:

```powershell
$policy = @{
    name = "Test: Label all emails"
    enabled = $true
    priority = 50
    action = "label_email"
    confidence_threshold = 0.7
    condition = @{
        exists = @("email_id")  # Matches all emails
    }
} | ConvertTo-Json -Depth 5

curl -X POST http://localhost:8003/api/actions/policies `
    -H "Content-Type: application/json" `
    -d $policy
```text

**Step 3: Propose Actions**

```powershell
# Propose actions for first 5 emails
$body = @{ email_ids = @(1,2,3,4,5) } | ConvertTo-Json

curl -X POST http://localhost:8003/api/actions/propose `
    -H "Content-Type: application/json" `
    -d $body
```text

**Step 4: View in UI**

1. Open <http://localhost:5175>
2. Click "Actions" button (top-right corner)
3. You should see proposed actions in the tray

**Step 5: Test "Always" Button**

1. Click "Always do this" on an action (purple button)
2. Should see toast: "✨ Policy created (ID: XX)"
3. Action will be automatically approved
4. Future similar emails will auto-execute

**Step 6: Verify Policy Created**

```powershell
# View all policies
curl http://localhost:8003/api/actions/policies | jq '.[] | select(.name | contains("Learned"))'
```text

**Step 7: Check Metrics**

```powershell
# View Prometheus metrics
curl http://localhost:8003/metrics | Select-String -Pattern "actions_"
```text

---

## Quick Test (Automated)

Run our test script:

```powershell
cd d:/ApplyLens
pwsh ./scripts/test-always-feature.ps1
```text

**Expected output:**

```text
=== Testing 'Always do this' Feature ===

[1/6] Checking API health...
✓ API is healthy (ApplyLens API)

[2/6] Proposing actions for sample emails...
✓ Created X proposed action(s)

[3/6] Fetching actions tray...
✓ Found X pending action(s)

[4/6] Creating learned policy via /always endpoint...
✓ Created learned policy (ID: XX)

[5/6] Verifying policy was created...
✓ Policy verified in database

[6/6] Checking Prometheus metrics...
✓ All metrics are exposed

🎉 All tests passed!
```text

---

## API Reference

### POST /api/actions/{action_id}/always

**Request:**

```json
{
  "rationale_features": {
    "category": "promotions",
    "sender_domain": "example.com",
    "risk_score": 0.15
  }
}
```text

**Response:**

```json
{
  "ok": true,
  "policy_id": 42
}
```text

**What it does:**

1. Extracts stable features (category, sender_domain)
2. Creates policy with `all` condition
3. Sets priority to 40 (learned policies)
4. Sets confidence threshold slightly lower than action
5. Enables policy immediately

**Example policy created:**

```json
{
  "name": "Learned: archive_email for example.com",
  "enabled": true,
  "priority": 40,
  "action": "archive_email",
  "confidence_threshold": 0.77,
  "condition": {
    "all": [
      {"eq": ["category", "promotions"]},
      {"eq": ["sender_domain", "example.com"]}
    ]
  }
}
```text

---

## Prometheus Metrics

### Metrics Exposed

```prometheus
# Total proposals by policy
actions_proposed_total{policy_name="High-risk auto-quarantine"} 12

# Successful executions by action type
actions_executed_total{action_type="archive_email",outcome="success"} 45

# Failed executions by action type and error
actions_failed_total{action_type="unsubscribe_via_header",error_type="No header"} 3
```text

### Useful Queries

**Proposal rate:**

```promql
rate(actions_proposed_total[5m])
```text

**Success rate:**

```promql
sum(rate(actions_executed_total{outcome="success"}[5m])) / 
(sum(rate(actions_executed_total[5m])) + sum(rate(actions_failed_total[5m])))
```text

**Top failing actions:**

```promql
topk(5, sum by (action_type) (rate(actions_failed_total[1h])))
```text

### Grafana Dashboard

Import this JSON to create a dashboard:

```json
{
  "dashboard": {
    "title": "ApplyLens Actions",
    "panels": [
      {
        "title": "Proposal Rate",
        "targets": [{
          "expr": "rate(actions_proposed_total[5m])"
        }],
        "type": "graph"
      },
      {
        "title": "Success Rate",
        "targets": [{
          "expr": "sum(rate(actions_executed_total{outcome=\"success\"}[5m])) / (sum(rate(actions_executed_total[5m])) + sum(rate(actions_failed_total[5m])))"
        }],
        "type": "gauge",
        "format": "percentunit"
      }
    ]
  }
}
```text

---

## PowerShell Quickruns

### Propose Actions

```powershell
# Propose for all emails matching a query
$body = @{ query = "category:promo OR risk_score:[80 TO *]"; limit = 50 } | ConvertTo-Json
curl -X POST http://localhost:8003/api/actions/propose -d $body | jq .
```text

### View Tray

```powershell
curl http://localhost:8003/api/actions/tray?limit=100 | jq '.[] | {id, action, confidence, email_subject}'
```text

### Approve First Action

```powershell
$firstId = curl -s http://localhost:8003/api/actions/tray | jq -r '.[0].id'
curl -X POST "http://localhost:8003/api/actions/$firstId/approve" -d '{}' | jq .
```text

### Create Learned Policy

```powershell
$firstId = curl -s http://localhost:8003/api/actions/tray | jq -r '.[0].id'
$body = @{
    rationale_features = @{
        category = "promotions"
        sender_domain = "example.com"
    }
} | ConvertTo-Json

curl -X POST "http://localhost:8003/api/actions/$firstId/always" `
    -H "Content-Type: application/json" `
    -d $body | jq .
```text

### View Learned Policies

```powershell
curl http://localhost:8003/api/actions/policies | jq '.[] | select(.name | contains("Learned"))'
```text

### View Metrics

```powershell
curl http://localhost:8003/metrics | Select-String -Pattern "actions_proposed_total"
```text

---

## Troubleshooting

### "No pending actions"

**Cause:** No emails match policy conditions

**Solution:**

1. Check policy conditions: `curl http://localhost:8003/api/actions/policies | jq '.[].condition'`
2. Check email data: `curl http://localhost:8003/api/search/?q=*&limit=5 | jq '.items[].category'`
3. Create test policy (see "Create Test Policy" above)
4. Or adjust policy conditions to match your emails

### "Failed to create policy"

**Cause:** No stable features in rationale

**Solution:**
Ensure rationale includes `features`:

```json
{
  "rationale": {
    "confidence": 0.82,
    "narrative": "...",
    "features": {
      "category": "promotions",
      "sender_domain": "example.com"
    }
  }
}
```text

Update `build_rationale()` in actions router to include features.

### "Metrics not showing up"

**Cause:** No actions proposed/executed yet

**Solution:**

1. Propose some actions (see above)
2. Approve/reject them
3. Metrics will appear after first event
4. Check: `curl http://localhost:8003/metrics | grep actions_`

### "API not responding"

**Cause:** Docker container stopped

**Solution:**

```powershell
cd d:/ApplyLens/infra
docker compose ps  # Check status
docker compose up -d api  # Start API
docker compose logs api  # Check logs
```text

### "Frontend can't connect to API"

**Cause:** Proxy misconfiguration

**Solution:**
Check `apps/web/vite.config.ts`:

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8003',
    changeOrigin: true,
  }
}
```text

Or access API directly: <http://localhost:8003/api/actions/tray>

---

## Next Steps

### For Users

1. ✅ Test "Always" button in UI
2. ✅ Create a few learned policies
3. ✅ Monitor metrics endpoint
4. ⏸️ Set up Grafana dashboard (optional)
5. ⏸️ Configure alerting (optional)

### For Developers

1. ✅ Review code changes (actions.py, metrics.py, actionsClient.ts)
2. ✅ Test API endpoints with curl
3. ⏸️ Write unit tests (test_yardstick_eval.py)
4. ⏸️ Write E2E tests (actions.tray.spec.ts)
5. ⏸️ Add ES aggregations to rationale

### For DevOps

1. ✅ Verify metrics endpoint exposed
2. ⏸️ Add Prometheus scrape config
3. ⏸️ Create Grafana dashboard
4. ⏸️ Set up alerting rules
5. ⏸️ Document runbooks

---

## Resources

**Documentation:**

- Full feature docs: `PHASE_4_ENHANCEMENTS_COMPLETE.md`
- Integration guide: `docs/PHASE_4_INTEGRATION_SUCCESS.md`
- Architecture: `docs/PHASE_4_SUMMARY.md`
- UI guide: `docs/PHASE_4_UI_GUIDE.md`

**Code:**

- Backend: `services/api/app/routers/actions.py` (line 450)
- Metrics: `services/api/app/telemetry/metrics.py`
- Client: `apps/web/src/lib/actionsClient.ts`
- UI: `apps/web/src/components/ActionsTray.tsx`

**Endpoints:**

- API Docs: <http://localhost:8003/docs>
- OpenAPI: <http://localhost:8003/openapi.json>
- Metrics: <http://localhost:8003/metrics>
- Frontend: <http://localhost:5175>

**Scripts:**

- Test suite: `scripts/test-always-feature.ps1`

---

## Support

**Questions?**

- Check documentation files in `docs/`
- Review OpenAPI spec: <http://localhost:8003/docs>
- Check logs: `docker compose logs api`

**Found a bug?**

- Check error logs
- Test with curl first (isolate frontend vs backend)
- Verify database state: `docker compose exec db psql -U applylens -c "SELECT * FROM policies LIMIT 5"`

**Feature requests?**

- Review pending work in `PHASE_4_ENHANCEMENTS_COMPLETE.md` section 8

---

## Summary

✅ **Feature is ready to use!**

**What works:**

- ✨ "Always do this" button creates learned policies
- 📊 Prometheus metrics track proposals/executions
- 🎨 UI provides clear feedback with toasts
- 🔒 Type-safe TypeScript integration
- 🐳 Deployed in Docker containers

**Try it now:**

```powershell
# Quick test
cd d:/ApplyLens
pwsh ./scripts/test-always-feature.ps1

# Or test in UI
# 1. Open http://localhost:5175
# 2. Click "Actions" button
# 3. Try "Always do this" on an action
```text

**Happy automating! 🚀**
