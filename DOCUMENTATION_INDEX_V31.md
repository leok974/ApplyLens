# Email Risk v3.1 - Documentation Index

**Last Updated:** October 21, 2025
**Status:** 🟢 **PRODUCTION READY**

---

## 📚 Complete Documentation Set

### 1. 🎯 Production Cutover (START HERE)

#### **CUTOVER_RUNBOOK_V31.md** ⭐ **PRIMARY GUIDE**
- **Purpose:** Step-by-step 15-minute cutover execution
- **Audience:** Platform team executing the cutover
- **Contains:**
  - 7-stage cutover timeline with commands
  - Validation checks for each stage
  - Expected outputs and success criteria
  - Rollback procedure (< 5 minutes)
  - 24-hour monitoring checklist
  - Prometheus queries for metrics
  - Troubleshooting guide

**When to use:** During actual production cutover execution

---

#### **PRE_FLIGHT_CHECKLIST_V31.md**
- **Purpose:** Pre-cutover validation (run 1 hour before)
- **Audience:** Platform lead, on-call engineer
- **Contains:**
  - 8 health checks with pass/fail criteria
  - Go/No-Go decision framework
  - Contact list and escalation path
  - Cutover timeline reference

**When to use:** 60 minutes before scheduled cutover

---

#### **CUTOVER_SUMMARY_V31.md**
- **Purpose:** High-level readiness overview
- **Audience:** Leadership, stakeholders, team briefing
- **Contains:**
  - Implementation status summary
  - Pre-flight validation results
  - Complete documentation inventory
  - Cutover timeline overview
  - Test results and metrics
  - Authorization sign-off section

**When to use:** Team briefings, stakeholder updates

---

### 2. 📖 Implementation Details

#### **STAGING_ENHANCEMENTS_COMPLETE.md**
- **Purpose:** Complete technical implementation documentation
- **Audience:** Engineers, technical reviewers
- **Contains:**
  - All 8 improvements detailed
  - Code changes with examples
  - Test results and verification
  - API endpoint documentation
  - Prometheus alert definitions
  - Production readiness assessment

**When to use:** Understanding what was built, code reviews

---

#### **STAGING_POST_CHECKLIST_V31.md**
- **Purpose:** Post-cutover verification guide
- **Audience:** Platform team, QA
- **Contains:**
  - 8-step verification procedure
  - Commands for each check
  - Expected outputs
  - Troubleshooting for common issues
  - Production sign-off checklist

**When to use:** After cutover completes, during validation

---

### 3. 🔧 Quick Reference

#### **QUICK_REFERENCE_V31.md**
- **Purpose:** Fast command lookup
- **Audience:** On-call engineers, daily operations
- **Contains:**
  - Quick command reference
  - Common troubleshooting snippets
  - Metrics thresholds
  - Test document details
  - Key file locations

**When to use:** Daily ops, quick lookups, troubleshooting

---

### 4. 🧪 Automation

#### **scripts/smoke_risk_advice.ps1**
- **Purpose:** Automated smoke testing
- **Audience:** Automation, CI/CD
- **Contains:**
  - 5-step automated test
  - Index test email
  - Query API endpoints
  - Verify metrics
  - Color-coded pass/fail output

**When to use:** Hourly monitoring, post-deployment validation

---

### 5. 📊 Monitoring

#### **infra/prometheus/alerts.yml** (Updated)
- **Purpose:** Alert rule definitions
- **Audience:** SRE, monitoring team
- **Contains:**
  - 4 Email Risk v3.1 alert rules:
    1. EmailRiskAdviceSpikeHigh
    2. EmailRiskAdviceDrop
    3. EmailRiskFeedbackAnomaly
    4. EmailRiskHighFalsePositives

**When to use:** Prometheus configuration, alert management

---

## 🗺️ Usage Flowchart

```
┌─────────────────────────────────────────────┐
│  PLANNING PHASE                             │
│  Read: CUTOVER_SUMMARY_V31.md              │
│  Read: STAGING_ENHANCEMENTS_COMPLETE.md    │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  PRE-CUTOVER (T-1 hour)                    │
│  Execute: PRE_FLIGHT_CHECKLIST_V31.md      │
│  Decision: Go / No-Go                       │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  CUTOVER EXECUTION (T+0 to T+15)           │
│  Execute: CUTOVER_RUNBOOK_V31.md ⭐        │
│  Reference: QUICK_REFERENCE_V31.md         │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  POST-CUTOVER VALIDATION (T+15 to T+30)    │
│  Execute: STAGING_POST_CHECKLIST_V31.md    │
│  Run: scripts/smoke_risk_advice.ps1        │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  MONITORING (24 hours)                      │
│  Watch: Prometheus alerts                   │
│  Run: smoke_risk_advice.ps1 (hourly)       │
│  Reference: QUICK_REFERENCE_V31.md         │
└─────────────────────────────────────────────┘
```

---

## 📋 Document Quick Access

| Document | Purpose | Primary Use |
|----------|---------|-------------|
| **CUTOVER_RUNBOOK_V31.md** ⭐ | Execution guide | During cutover |
| **PRE_FLIGHT_CHECKLIST_V31.md** | Validation | Before cutover |
| **CUTOVER_SUMMARY_V31.md** | Overview | Briefings |
| **STAGING_ENHANCEMENTS_COMPLETE.md** | Technical details | Understanding implementation |
| **STAGING_POST_CHECKLIST_V31.md** | Verification | After cutover |
| **QUICK_REFERENCE_V31.md** | Commands | Daily ops |

---

## 🎯 Key Sections by Role

### Platform Engineer (Executing Cutover)
1. Read: **CUTOVER_RUNBOOK_V31.md** (sections 1-7)
2. Reference: **QUICK_REFERENCE_V31.md** (commands)
3. Fallback: **CUTOVER_RUNBOOK_V31.md** (rollback section)

### Platform Lead (Go/No-Go Decision)
1. Review: **PRE_FLIGHT_CHECKLIST_V31.md** (all checks)
2. Approve: **CUTOVER_SUMMARY_V31.md** (sign-off)
3. Brief: Team using **CUTOVER_SUMMARY_V31.md**

### On-Call Engineer (Monitoring)
1. Monitor: Prometheus dashboards
2. Run: **scripts/smoke_risk_advice.ps1** (hourly)
3. Reference: **QUICK_REFERENCE_V31.md** (troubleshooting)
4. Escalate: Use **CUTOVER_RUNBOOK_V31.md** (rollback if needed)

### QA Engineer (Validation)
1. Execute: **STAGING_POST_CHECKLIST_V31.md** (8 steps)
2. Run: **scripts/smoke_risk_advice.ps1**
3. Document: Results in checklist sign-off

### Product Owner (Feature Flag)
1. Review: **CUTOVER_SUMMARY_V31.md** (timeline T+13)
2. Configure: EmailRiskBanner flag (10% → 100%)
3. Monitor: False positive feedback

---

## 🔍 Finding Information

### "How do I execute the cutover?"
→ **CUTOVER_RUNBOOK_V31.md** (start at Step 1)

### "What improvements were made?"
→ **STAGING_ENHANCEMENTS_COMPLETE.md** (sections 1-8)

### "How do I verify it's working?"
→ **STAGING_POST_CHECKLIST_V31.md** (8-step verification)

### "What's the quick command for X?"
→ **QUICK_REFERENCE_V31.md** (command reference)

### "Are we ready to go?"
→ **PRE_FLIGHT_CHECKLIST_V31.md** (run all checks)

### "Something went wrong, rollback!"
→ **CUTOVER_RUNBOOK_V31.md** (Rollback Procedure section)

### "What are the test results?"
→ **CUTOVER_SUMMARY_V31.md** (Test Results section)

### "What alerts should I watch?"
→ **CUTOVER_RUNBOOK_V31.md** (Monitoring Checklist section)

---

## 📊 Implementation Summary

### All 8 Improvements Complete ✅

1. **Cross-Index Queries** - `/emails/{id}/risk-advice` with fallback
2. **Prometheus Metrics** - `applylens_email_risk_served_total{level}`
3. **Domain Enrichment** - Backfill via reindex
4. **Prime-Advice Endpoint** - `POST /emails/{id}/prime-advice`
5. **Kibana Data View** - `gmail_emails-*` pattern
6. **Smoke Test Script** - `scripts/smoke_risk_advice.ps1`
7. **Prometheus Alerts** - 4 Email Risk v3.1 rules
8. **Post-Staging Checklist** - Verification guide

### Test Results ✅

- **Score:** 78/100
- **Status:** Suspicious
- **Signals:** 6 detected
- **From:** security@paypa1-verify.com
- **Subject:** "Urgent: Verify Your Account Now"

### System Health ✅

- **API:** Running (applylens-api-prod)
- **Elasticsearch:** Yellow (single node, acceptable)
- **Prometheus:** Healthy and scraping
- **Metrics:** Incrementing correctly

---

## 🚀 Next Steps

### Immediate
1. **Review** `CUTOVER_RUNBOOK_V31.md`
2. **Schedule** cutover window
3. **Execute** `PRE_FLIGHT_CHECKLIST_V31.md` (T-1 hour)
4. **Brief** team on cutover plan

### During Cutover (15 minutes)
1. Follow `CUTOVER_RUNBOOK_V31.md` steps 1-7
2. Reference `QUICK_REFERENCE_V31.md` for commands
3. Validate each stage before proceeding

### Post-Cutover (24 hours)
1. Execute `STAGING_POST_CHECKLIST_V31.md`
2. Run `scripts/smoke_risk_advice.ps1` hourly
3. Monitor Prometheus alerts
4. Collect user feedback

### 1 Week
1. Review false positive rate (target: <10%)
2. Tune signal weights if needed
3. Ramp feature flag to 100%
4. Complete retrospective

---

## 📞 Support

**Primary Contact:** Platform Engineering Team
**Slack Channel:** #email-risk-v31
**On-Call:** PagerDuty rotation
**Escalation:** See `PRE_FLIGHT_CHECKLIST_V31.md`

**Emergency Rollback:** See `CUTOVER_RUNBOOK_V31.md` (Rollback Procedure)

---

## ✅ Status

**Implementation:** 🟢 Complete (8/8)
**Pre-Flight:** 🟢 All checks passed
**Documentation:** 🟢 Complete (6 files)
**Testing:** 🟢 Smoke test passing
**Monitoring:** 🟢 Alerts configured

**OVERALL STATUS:** 🟢 **PRODUCTION READY**

---

**Last Updated:** October 21, 2025
**Next Review:** Post-cutover retrospective (T+7 days)
**Owner:** Platform Engineering Team
