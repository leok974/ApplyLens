# Email Risk v3.1 - Pre-Flight Checklist

**Date:** October 21, 2025
**Cutover Time:** [SCHEDULE: ____________]
**Estimated Duration:** 15 minutes
**Team:** Platform Engineering

---

## ✅ Pre-Cutover Validation (Run 1 Hour Before)

### 1. System Health
```powershell
# Check all services running
docker-compose -f docker-compose.prod.yml ps

# Expected: All services "Up"
# - applylens-api-prod
# - applylens-es-prod
# - applylens-web-prod
# - applylens-db-prod
```
**Status:** ☐ Pass ☐ Fail

### 2. Staging Tests Passing
```powershell
# Run smoke test
cd d:\ApplyLens
.\scripts\smoke_risk_advice.ps1

# Expected: "✅ PASS - All critical checks successful"
```
**Status:** ☐ Pass ☐ Fail

### 3. Prometheus Healthy
```bash
# Check Prometheus targets
curl -s http://localhost:9090/api/v1/targets | `
  jq '.data.activeTargets[] | select(.labels.job=="applylens-api") | {health: .health}'

# Expected: {"health": "up"}
```
**Status:** ☐ Pass ☐ Fail

### 4. Elasticsearch Cluster Green
```bash
docker exec applylens-es-prod curl -s http://localhost:9200/_cluster/health | `
  jq '{status, number_of_nodes}'

# Expected: {"status": "green" or "yellow", "number_of_nodes": 1}
```
**Status:** ☐ Pass ☐ Fail

### 5. Backup Verified
```bash
# Check pipeline backup exists
ls -la d:\ApplyLens\infra\elasticsearch\pipelines\backup\

# Expected: emails_v2_backup_20251021_*.json
```
**Status:** ☐ Pass ☐ Fail

### 6. Alert Rules Staged
```bash
# Verify alerts file updated
cat d:\ApplyLens\infra\prometheus\alerts.yml | `
  Select-String "applylens_email_risk_v31"

# Expected: Shows 4 Email Risk v3.1 alert rules
```
**Status:** ☐ Pass ☐ Fail

### 7. Documentation Ready
```powershell
# Check runbook exists
Test-Path d:\ApplyLens\CUTOVER_RUNBOOK_V31.md

# Check all enhancement docs
Test-Path d:\ApplyLens\STAGING_ENHANCEMENTS_COMPLETE.md
Test-Path d:\ApplyLens\STAGING_POST_CHECKLIST_V31.md
Test-Path d:\ApplyLens\QUICK_REFERENCE_V31.md
```
**Status:** ☐ Pass ☐ Fail

### 8. Team Notification Sent
- [ ] Platform team notified (Slack #email-risk-v31)
- [ ] On-call engineer aware
- [ ] Product team informed (feature flag ramp schedule)
- [ ] Security team CC'd (false positive monitoring)

---

## 📋 Cutover Readiness

| Item | Status | Notes |
|------|--------|-------|
| All services healthy | ☐ | Check docker-compose ps |
| Smoke test passing | ☐ | Run scripts/smoke_risk_advice.ps1 |
| Prometheus up | ☐ | Check targets endpoint |
| ES cluster green/yellow | ☐ | Check cluster health |
| Backup exists | ☐ | Verify v2 pipeline backup |
| Alert rules ready | ☐ | Check alerts.yml updated |
| Documentation complete | ☐ | 4 files present |
| Team notified | ☐ | Slack + PagerDuty |

**All checks passed?** ☐ Yes → **Proceed with cutover**
**Any checks failed?** ☐ Yes → **Delay cutover, investigate**

---

## 🎯 Go/No-Go Decision

**Reviewed By:** _______________ Time: _______________

**Decision:** ☐ GO ☐ NO-GO

**If NO-GO, reason:** _______________________________________________

---

## 📞 Contact List

| Role | Name | Contact |
|------|------|---------|
| Platform Lead | ______ | Slack: @______ |
| On-Call Engineer | ______ | PagerDuty: ______ |
| Product Owner | ______ | Slack: @______ |
| Security Lead | ______ | Slack: @______ |

---

## ⏱️ Cutover Timeline Reference

```
T+0  → Lock templates + pipeline (2 min)
T+2  → Switch default pipeline (2 min)
T+4  → Sanity check doc shape (2 min)
T+6  → API verification (3 min)
T+9  → Prometheus reload (2 min)
T+11 → Kibana validation (2 min)
T+13 → Feature flag ramp (2 min)
---
T+15 → CUTOVER COMPLETE
```

**Start Time:** _______________
**Expected Completion:** _______________

---

**Last Updated:** October 21, 2025
