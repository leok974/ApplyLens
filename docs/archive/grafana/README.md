# Grafana Legacy Documentation Archive

**Archived Date**: November 25, 2025
**Reason**: Datadog is now the primary observability provider for ApplyLens.

---

## Status

Prometheus and Grafana are **marked as legacy** but still running in production for:
- Historical metrics data
- Transition period monitoring
- Backup observability

**Primary Observability**: Datadog (as of November 2025)

---

## What's in this archive

- Grafana dashboard setup guides
- Grafana plugin installation scripts
- Legacy dashboard JSON files
- Prometheus-specific metric documentation

---

## Decommissioning Plan

**Phase 3** (Future):
1. Verify all alerts migrated to Datadog monitors
2. Export historical Prometheus data if needed
3. Stop Prometheus + Grafana containers
4. Archive remaining configs to `/infra/archive/`

---

**Reference**:
- Phase 1 Audit: `docs/REPO_AUDIT_PHASE1.md`
- Phase 2 Summary: `docs/REPO_CLEANUP_PHASE2_SUMMARY.md`
- Current Observability: See `hackathon/DATADOG_SETUP.md`
