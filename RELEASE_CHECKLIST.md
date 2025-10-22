# Email Risk v3.1 — Release Checklist

**Version:** v3.1-prod-stable
**Target Release Date:** TBD
**Status:** 🟢 Ready for Production Certification

---

## Pre-Release Verification ✅

### 1. Testing (Complete)
- [x] Backend unit tests passing (8/8 tests)
  - `pytest services/api/tests/api/test_email_risk.py -v`
  - Coverage: `app/routers/emails.py` 51%
  - All BadRequest fallback scenarios tested
- [x] Frontend unit tests passing (10/10 tests)
  - `pnpm --filter web test -- --run`
  - Feature flag logic verified (hashToBucket, isUserInRollout, gradual rollout)
- [x] Smoke test passing (0 failures)
  - `pwsh ./scripts/smoke_risk_advice.ps1`
  - Score: 78 (expected 66+), 6 signals detected
  - Exit code: 0
- [x] Grafana dashboard accessible
  - URL: http://localhost:3000/d/email-risk-v31
  - P95 latency panel with 300ms/500ms thresholds
- [ ] Kibana data view validated
  - Manual import via UI pending
  - Saved searches exist in `infra/kibana/saved_searches_v31.ndjson`

### 2. CI/CD Integration
- [x] GitHub Actions workflow updated
  - File: `.github/workflows/ci.yml`
  - Jobs: backend-unit, web-unit, smoke-risk, all-checks
  - Branch protection: Require all checks green
- [x] Feature flag ramp endpoint deployed
  - Router: `services/api/app/routers/flags.py`
  - Endpoints: GET/POST /flags/{flag}/ramp
  - Audit logging enabled
- [x] Weight tuning script available
  - Script: `scripts/analyze_weights.py --since 7d`
  - Generates: `WEIGHT_TUNING_ANALYSIS.md`

### 3. Observability
- [x] Prometheus metrics verified
  - `applylens_email_risk_served_total{level="suspicious"}` = 4.0
  - `applylens_crypto_decrypt_error_total` initialized
- [x] Grafana P50/P95 panels configured
  - P50 < 300ms (green), < 500ms (orange), >= 500ms (red)
  - P95 < 300ms target
- [ ] Prometheus reload executed
  - Command: `curl -X POST http://localhost:9090/-/reload`
- [ ] Alert rules loaded
  - File: `infra/prometheus/alerts/email_risk_v31.yml`
  - Alerts: HighErrorRate, SlowP95Latency, DecryptErrors, RateLimitExceeded

---

## Deployment Stages 🚀

### Stage 1: Soft Launch (10% rollout) — Day 0
- [ ] Ramp EmailRiskBanner to 10%
  ```bash
  curl -X POST 'http://localhost:8003/flags/EmailRiskBanner/ramp?to=10'
  ```
- [ ] Monitor for 6 hours
  - P95 latency < 300ms sustained
  - Error rate < 0.1%
  - No decrypt errors
  - User feedback: < 5% false positive reports
- [ ] Verify Grafana dashboard shows real-time data
- [ ] Check audit log: `curl http://localhost:8003/flags/EmailRiskBanner/audit`

### Stage 2: Gradual Ramp (25% rollout) — Day 1 (T+24h)
- [ ] Verify Stage 1 metrics stable
- [ ] Ramp to 25%
  ```bash
  curl -X POST 'http://localhost:8003/flags/EmailRiskBanner/ramp?to=25'
  ```
- [ ] Monitor for 12 hours
- [ ] Run first weight analysis
  ```bash
  python scripts/analyze_weights.py --since 24h --output docs/WEIGHT_TUNING_ANALYSIS_D1.md
  ```

### Stage 3: Broader Rollout (50% rollout) — Day 3 (T+72h)
- [ ] Ramp to 50%
- [ ] Monitor for 24 hours
- [ ] Review weight tuning recommendations
- [ ] Apply approved weight changes (if any)

### Stage 4: Full Deployment (100% rollout) — Day 7 (T+168h)
- [ ] Ramp to 100%
- [ ] All SLOs met for 48 consecutive hours
- [ ] No P1 incidents related to Email Risk

---

## Production Certification Criteria ✅

### Performance SLOs
- [ ] **P50 latency** < 200ms (99th percentile over 7 days)
- [ ] **P95 latency** < 300ms (99th percentile over 7 days)
- [ ] **Error rate** < 0.1% (5xx responses)
- [ ] **Rate limit exceed rate** < 1%

### Quality Metrics
- [ ] **Precision** ≥ 85% (from user feedback analysis)
- [ ] **Recall** ≥ 75% (catching actual scam/phishing)
- [ ] **False positive rate** < 10%
- [ ] **User satisfaction** ≥ 80% (from banner dismiss rate)

### Operational Readiness
- [ ] Prometheus alerts firing correctly (test with synthetic failure)
- [ ] On-call runbook documented
- [ ] Rollback procedure tested
- [ ] Feature flag kill switch verified (`POST /flags/EmailRiskBanner/disable`)

---

## Release Artifacts 📦

### Git Tags
- [ ] Tag created: `v3.1-prod-stable`
  ```bash
  git tag -a v3.1-prod-stable -m "Email Risk v3.1 — Production Stable Release"
  git push origin v3.1-prod-stable
  ```

### Release Notes
- [ ] GitHub release created with:
  - **Summary:** Email Risk v3.1 with BadRequest fallback, feature flags, and enhanced observability
  - **Commit SHA:** (insert after tagging)
  - **Docker Image Digest:** `ghcr.io/leok974/applylens/api:v3.1-prod-stable@sha256:...`
  - **Grafana Dashboard:** http://localhost:3000/d/email-risk-v31
  - **Kibana Searches:** Imported from `infra/kibana/saved_searches_v31.ndjson`

### Documentation
- [ ] Export Grafana dashboard JSON
  ```bash
  curl -s 'http://localhost:3000/api/dashboards/uid/email-risk-v31' | \
    jq '.dashboard' > releases/v3.1/email_risk_v31_dashboard.json
  ```
- [ ] Export Prometheus alert rules
  ```bash
  cp infra/prometheus/alerts/email_risk_v31.yml releases/v3.1/
  ```
- [ ] Archive to release assets

---

## Post-Release Activities 📊

### Week 1
- [ ] **Day 1:** Run weight analysis (24h feedback)
- [ ] **Day 3:** Run weight analysis (72h feedback)
- [ ] **Day 7:** Run weight analysis (7d feedback)
- [ ] **Day 7:** Review all weight tuning recommendations
- [ ] **Day 7:** Open PR with approved weight changes

### Week 2
- [ ] Apply weight adjustments (if approved)
- [ ] Monitor impact on precision/recall
- [ ] Document learnings in `docs/EMAIL_RISK_V31_POSTMORTEM.md`

### Ongoing
- [ ] Schedule weekly weight analysis (cron job)
- [ ] Monitor P95 latency trends
- [ ] Track user feedback patterns
- [ ] Plan v3.2 features (feedback-weighted heuristics, reputation API)

---

## Rollback Procedure 🔄

**If any SLO is violated or P1 incident occurs:**

1. **Immediate:** Disable feature flag
   ```bash
   curl -X POST 'http://localhost:8003/flags/EmailRiskBanner/disable'
   ```

2. **Within 5 minutes:** Verify banner no longer shown to users

3. **Within 15 minutes:** Investigate root cause
   - Check Grafana dashboard for anomalies
   - Review Elasticsearch logs: `docker logs applylens-api-prod --tail 100`
   - Check Prometheus alerts

4. **Within 30 minutes:** Incident response
   - Notify team via Slack
   - Create incident ticket
   - Begin root cause analysis

5. **Within 24 hours:** Post-incident review
   - Document timeline
   - Identify prevention measures
   - Update runbook

---

## Sign-Off 📝

**Engineering Lead:**
- Name: _____________
- Date: _____________
- Signature: _____________

**Product Manager:**
- Name: _____________
- Date: _____________
- Signature: _____________

**SRE/Operations:**
- Name: _____________
- Date: _____________
- Signature: _____________

---

## Status Dashboard

| Criterion | Status | Notes |
|-----------|--------|-------|
| Backend Tests | ✅ PASS | 8/8 passing |
| Frontend Tests | ✅ PASS | 10/10 passing |
| Smoke Test | ✅ PASS | 0 failures |
| CI/CD | ✅ READY | Workflows configured |
| Grafana | ✅ READY | Dashboard accessible |
| Kibana | ⚠️ PENDING | Manual import needed |
| 10% Rollout | ⏳ PENDING | Awaiting go-live |
| 100% Rollout | ⏳ PENDING | Staged deployment |
| Prod Certified | ⏳ PENDING | Awaiting SLO validation |

**Overall Status:** 🟢 **READY FOR SOFT LAUNCH**

**Next Action:** Execute Stage 1 (10% rollout) and monitor for 6 hours.
