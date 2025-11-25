# Legacy Scripts Archive

**Date Archived**: November 25, 2025
**Reason**: These scripts were identified in Phase 2 cleanup as legacy/unclear and moved here for safekeeping.

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
**Can Delete After**: Verify pipeline v2 is stable and no rollback needed.

---

### Old Deployment Scripts
Superseded by newer deployment workflows:
- `deploy_email_risk_v3.sh`
- `deploy_email_risk_v31.sh`
- `deploy-today-panel.ps1`
- `phase2-all.ps1`

**Status**: Legacy - newer versions exist or feature deployment is complete.
**Can Delete After**: Confirm features are stable in production.

---

### Duplicate/Unclear CI Scripts
May be duplicates of PowerShell equivalents:
- `ci-smoke-es-email-v2.sh`
- `ci-smoke-test.sh`

**Status**: Likely duplicates of `.ps1` versions.
**Can Delete After**: Confirm CI uses `.ps1` versions exclusively.

---

### AWS/GCP Migration Scripts
AWS-related scripts when we were on AWS:
- `rotate_secret_aws.sh` - AWS Secrets Manager rotation
- `aws_secrets.sh` - AWS Secrets Manager provisioning
- `generate_aes_key.py` - One-time AES key generation utility

**Status**: Obsolete - now using GCP.
**Can Delete After**: Confirm no AWS infrastructure remains.

---

### Testing & Development Utilities
One-time testing and development tools:
- `BackfillCheck.ps1` - Manual backfill testing with Windows toast notifications
- `create-test-policy.ps1` - Demo policy creation for testing
- `analyze_weights.py` - Email risk v3.1 weight tuning analysis
- `test_es_template.py` - ES pipeline v2 validation
- `upload_pipeline.py` - Manual ES pipeline upload (now automated)
- `test-port-forwarding.ps1` - Network connectivity testing

**Status**: Development/testing utilities no longer in active use.
**Can Delete After**: Verify equivalent functionality exists in current tooling.

---

### Observability (Pre-Datadog)
Grafana/Kibana scripts before Datadog migration:
- `kibana-import.sh` (duplicate of `.ps1` version)

**Status**: Legacy - Datadog is primary observability now (Nov 2025).
**Can Delete After**: Grafana fully decommissioned (Phase 3).

---

## Summary Statistics

- **Total Scripts**: 19
- **Archived in Phase 2**: 11 (Nov 25, 2025)
- **Archived in Phase 2.5**: 8 (Nov 25, 2025)
- **Next Review**: 2026-01-31

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
**Reference**: See `docs/REPO_CLEANUP_PHASE2_SUMMARY.md`
