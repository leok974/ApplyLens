# ApplyLens Documentation Index

**Last Updated:** October 20, 2025  
**Version:** Production v1.0  
**Status:** ✅ Production Ready

Welcome to the ApplyLens documentation. This index provides quick access to all documentation organized by topic.

---

## 🚀 Quick Start

### For Deployment
1. **[Production Deployment Checklist](PRODUCTION_DEPLOYMENT_CHECKLIST.md)** - Complete deployment checklist
2. **[Deployment Finalized](DEPLOYMENT_FINALIZED.md)** - Deployment summary and verification
3. **[Finalization Checklist](FINALIZATION_CHECKLIST_2025-10-20.md)** - Detailed implementation guide

### For Development
1. **[E2E Auth Tests](E2E_AUTH_TESTS_2025-10-20.md)** - End-to-end authentication test results
2. **[Security Implementation](SECURITY_IMPLEMENTATION_2025-10-19.md)** - Security architecture
3. **[Success Summary](SUCCESS_SUMMARY.md)** - Quick reference guide

### For Operations
1. **[Monitoring Cheatsheet](MONITORING_CHEATSHEET.md)** - Prometheus/Grafana usage
2. **Pre-Deploy Validation:** `.\scripts\pre-deploy-check.ps1`
3. **Quick Smoke Tests:** `.\scripts\quick-smoke.ps1`

---

## 📚 All Documentation Files

### Deployment Documentation
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md` - Complete operational checklist
- `DEPLOYMENT_FINALIZED.md` - Final deployment summary with troubleshooting
- `FINALIZATION_CHECKLIST_2025-10-20.md` - 9-item security hardening guide
- `FINALIZATION_COMPLETE.md` - High-level finalization summary

### Security Documentation
- `SECURITY_IMPLEMENTATION_2025-10-19.md` - Complete security architecture
- `E2E_AUTH_TESTS_2025-10-20.md` - 7 authentication test scenarios

### Monitoring Documentation
- `MONITORING_CHEATSHEET.md` - Prometheus/Grafana reference guide
- `ALERT_RESOLUTION_DependenciesDown_2025-10-20.md` - DependenciesDown alert resolution
- `ALERT_STATUS_HighHttpErrorRate_2025-10-20.md` - HighHttpErrorRate alert status

### Infrastructure Setup
- `SETUP_ES_PIPELINE_GRAFANA_DASHBOARD.md` - Elasticsearch pipeline & Grafana dashboard setup
- `EMAIL_PIPELINE_SETUP_2025-10-20.md` - Email ingest pipeline v1 with ILM and templates
- `EMAIL_PIPELINE_V2_DASHBOARD_2025-10-20.md` - Email pipeline v2 (smart flags) + dashboard bundle
- `PIPELINE_V2_VALIDATION_2025-10-20.md` - Pipeline v2 validation & sanity checks ✅
- `NEXT_STEPS_PIPELINE_V2.md` - Next steps: reindex & query guide 🚀
- `EMAIL_INFRASTRUCTURE_APPLIED_2025-10-20.md` - Email infrastructure application summary
- `KIBANA_SETUP_2025-10-20.md` - Kibana data view & saved search for email exploration
- `KIBANA_LENS_VISUALIZATIONS_2025-10-20.md` - Kibana Lens visualizations & saved searches
- `KIBANA_VISUALIZATIONS_APPLIED_2025-10-20.md` - Kibana visualizations deployment summary
- `COMPLETE_INFRASTRUCTURE_SUMMARY_2025-10-20.md` - Complete infrastructure overview
- `ARTIFACTS_APPLIED_2025-10-20.md` - Infrastructure artifacts applied

### Quick Reference
- `SUCCESS_SUMMARY.md` - Quick start and common commands
- `DOC_INDEX.md` (this file) - Documentation index

---

## 🔧 Scripts

### Pre-Deployment Validation
- `scripts/pre-deploy-check.sh` - Bash version
- `scripts/pre-deploy-check.ps1` - PowerShell version
- Validates 12+ environment variables

### Quick Smoke Tests
- `scripts/quick-smoke.sh` - Bash version
- `scripts/quick-smoke.ps1` - PowerShell version
- 4 tests in ~5 seconds

### Pipeline v2 Scripts
- `scripts/test_es_template.py` - CI guard for template validation
- `scripts/reindex_to_pipeline_v2.ps1` - Reindex emails through pipeline v2
- `scripts/test_pipeline_v2_queries.ps1` - Test KQL queries with smart flags

---

## 🎯 Common Commands

```powershell
# Pre-deployment
.\scripts\pre-deploy-check.ps1

# Smoke tests
.\scripts\quick-smoke.ps1

# View Grafana
Start-Process "http://localhost:3000/dashboards"

# View Prometheus
Start-Process "http://localhost:9090/alerts"

# Check service health
docker ps --filter "name=applylens-*-prod"
```

---

**Last Updated:** October 20, 2025  
**Status:** ✅ Production Ready
