# Legacy Scripts Archive

**Date Archived**: November 25, 2025
**Reason**: These scripts were identified in REPO_AUDIT_PHASE1.md as legacy/unclear and moved here for safekeeping.

## ⚠️ IMPORTANT

**DO NOT DELETE** these scripts without explicit confirmation that they are no longer needed.

These files may still have historical value or contain logic that could be useful for reference.

---

## Script Categories

### One-Time Pipeline Fixes
These were used for one-time data migrations or bug fixes:
- `fix_pipeline_final.py`
- `fix_pipeline_json.py`
- `fix_pipeline_triple_quotes.py`

**Status**: Likely obsolete after pipeline stabilization.
**Last Used**: Unknown (pre-audit)
**Can Delete After**: Verify pipeline v2 is stable and no rollback needed.

---

### Old Deployment Scripts
Superseded by newer deployment workflows:
- `deploy_email_risk_v3.sh`
- `deploy_email_risk_v31.sh`
- `deploy-today-panel.ps1`
- `phase2-all.ps1`

**Status**: Legacy - newer versions exist or feature deployment is complete.
**Last Used**: Unknown (pre-2025-11)
**Can Delete After**: Confirm features are stable in production.

---

### Duplicate/Unclear CI Scripts
May be duplicates of PowerShell equivalents:
- `ci-smoke-es-email-v2.sh`
- `ci-smoke-test.sh`

**Status**: Likely duplicates of `.ps1` versions.
**Last Used**: Unknown
**Can Delete After**: Confirm CI uses `.ps1` versions exclusively.

---

### Old Secrets Rotation
AWS-related scripts when we were on AWS:
- `rotate_secret_aws.sh`

**Status**: Obsolete - now using GCP.
**Last Used**: Pre-GCP migration
**Can Delete After**: Confirm no AWS infrastructure remains.

---

### Old Grafana/Kibana Setup Scripts
Grafana is now legacy (Datadog is primary):
- `kibana-import.sh` (duplicate of `.ps1` version)
- `install_grafana_plugin.ps1`
- `start_grafana_docker.ps1`

**Status**: Legacy - Datadog is primary observability now.
**Last Used**: Pre-Datadog migration (2025-11)
**Can Delete After**: Grafana fully decommissioned.

---

## Review Schedule

**Next Review**: 2025-12-31
**Action**: If no one objects by then, these can be permanently deleted.

---

## How to Restore a Script

If you need to restore any script:

```bash
# Move it back to scripts/
git mv scripts/legacy/<script_name> scripts/<script_name>
git commit -m "chore: restore <script_name> from legacy"
```

---

**Archived by**: Phase 2 Repo Cleanup
**Reference**: See `docs/REPO_AUDIT_PHASE1.md` and `docs/REPO_CLEANUP_PHASE2_SUMMARY.md`
