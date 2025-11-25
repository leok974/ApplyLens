# chore(repo): Phase 2 cleanup – security, artifacts, legacy organization

## Summary

Phase 2 repository cleanup has been completed following the comprehensive audit in `REPO_AUDIT_PHASE1.md`. This cleanup focuses on **safe, non-destructive organization** with no production code deletions. All changes are reversible and fully documented.

Key accomplishments:
- **Hardened `.gitignore`** to prevent future commits of coverage files, debug artifacts, certificates, and logs
- **Removed tracked artifacts** (~800KB): backup docker-compose files, debug JSON, coverage reports
- **Organized legacy scripts** into `scripts/legacy/` with comprehensive README explaining status
- **Archived historical documentation** to `docs/archive/{grafana,phases,patches}/` with explanatory READMEs
- **Annotated Prometheus/Grafana as legacy** in docker-compose files (Datadog is now primary observability)
- **Flagged ambiguous code** with STATUS comments and review deadline (2025-12-31)

No git history was rewritten, no production services were removed, and all docker-compose configurations remain fully functional.

---

## Changes by Area

### 🔒 Security & .gitignore
- ✅ **Verified no secrets/certificates tracked** - `secrets/`, `letsencrypt/`, `*.pem`, `*.key`, `*.crt` all clear
- ✅ **Hardened `.gitignore`** with additional patterns:
  - `coverage.lcov` - Test coverage reports
  - `*.spec.ts-snapshots/` - Playwright snapshots
  - `.ruff_cache/` - Python linter cache
  - `*-debug.json`, `openapi-debug.json` - Debug artifacts
  - `letsencrypt/**`, `*.crt`, `*.p12` - Certificates

### 🧹 Artifacts & Backups
**Removed from git tracking** (6 files, ~800KB):
- `docker-compose.prod.yml.backup`
- `docker-compose.tunnel.yml.backup`
- `services/api/openapi-debug.json` (467KB)
- `services/api/coverage.lcov` (296KB)

**Deleted from disk** (untracked):
- `docker-compose.prod.yml.20251023-114511.bak`
- `scripts/backfill-errors.log` (37KB)

### 📁 Scripts & Legacy Organization
**Created**: `scripts/legacy/` directory with comprehensive README

**Moved 11 legacy scripts**:
- Pipeline fixes: `fix_pipeline_final.py`, `fix_pipeline_json.py`, `fix_pipeline_triple_quotes.py`
- Old deployments: `deploy_email_risk_v3.sh`, `deploy_email_risk_v31.sh`, `deploy-today-panel.ps1`, `phase2-all.ps1`
- Duplicate CI: `ci-smoke-es-email-v2.sh`, `ci-smoke-test.sh`
- AWS migration: `rotate_secret_aws.sh`
- Kibana duplicate: `kibana-import.sh`

**Flagged 8 ambiguous scripts** with STATUS comments (review by 2025-12-31):
- `aws_secrets.sh`, `BackfillCheck.ps1`, `create-test-policy.ps1`, `generate_aes_key.py`
- `analyze_weights.py`, `test_es_template.py`, `test-port-forwarding.ps1`, `upload_pipeline.py`

### 📚 Docs & Observability
**Created archive structure**:
```
docs/archive/
├── grafana/     (9 files - Grafana setup, dashboards, scripts)
├── phases/      (14 files - PHASE_* and *_COMPLETE.md milestones)
└── patches/     (4 files - PATCH_* and NEXT_STEPS_* historical notes)
```

**Archived 27 documentation files**:
- **Grafana docs** → `docs/archive/grafana/` (legacy - Datadog is primary)
- **Phase snapshots** → `docs/archive/phases/` (historical implementation milestones)
- **Patch notes** → `docs/archive/patches/` (completed fixes and migrations)

All archive directories include explanatory READMEs with deprecation notices and references to current documentation.

### 🐳 Docker Annotations
**Updated `docker-compose.prod.yml`**:
- Added header comment marking Prometheus/Grafana as **LEGACY** (Datadog is primary as of Nov 2025)
- Documented retention rationale: historical data, safe transition, Phase 3 decommissioning
- Added section comments on Prometheus and Grafana services with references to `hackathon/DATADOG_SETUP.md`

**Updated `docker-compose.edge.yml`**:
- Added "STATUS: Unclear usage. Needs review." comment
- Documented potential supersession by Cloudflare Tunnel

**Updated `docker-compose.hackathon.yml`**:
- Added header documenting hackathon/demo purpose (Datadog + Gemini integration)
- Marked as non-production stack

**No services removed** - all containers remain functional.

### 💬 Code Comments / TODOs
**Added README files to ambiguous root directories**:
- `src/README.md` - Empty directory, likely legacy (review needed)
- `public/README.md` - Contains `metrics.html`, may be duplicate of `apps/web/public`
- `tests/README.md` - 18 E2E tests, may overlap with `apps/web/e2e`

All flagged for review by **2025-12-31** to determine if they should be consolidated or removed.

---

## Risk / Impact

### ✅ Zero Production Risk
- **No production code paths removed** - all active scripts, services, and configurations remain unchanged
- **No environment variables modified** - deployment configurations untouched
- **No running containers affected** - docker-compose services fully operational
- **No breaking changes** - all changes are organizational/documentary

### ✅ Fully Reversible
- Files moved with `git mv` (trackable in git history)
- No deletions from git history (Phase 2 does not rewrite history)
- All archives documented with restoration instructions
- Legacy scripts can be moved back with single `git mv` command

### ⚠️ Minor Considerations
- `.gitignore` patterns should be tested to ensure no required files are blocked
- Team should review flagged items before 2025-12-31 deadline
- Prometheus/Grafana still running (decommissioning planned for Phase 3)

---

## Review Checklist

### Documentation
- [ ] Confirm `docs/REPO_CLEANUP_PHASE2_SUMMARY.md` matches the diff
- [ ] Review `docs/REPO_AUDIT_PHASE1.md` for context on flagged items
- [ ] Verify all archive READMEs (`docs/archive/{grafana,phases,patches}/README.md`) are clear
- [ ] Check `scripts/legacy/README.md` explains why each script was moved

### Configuration
- [ ] Sanity-check `.gitignore` patterns (no over-blocking of required files)
- [ ] Verify docker-compose annotations in `docker-compose.prod.yml` are accurate
- [ ] Confirm `docker-compose.edge.yml` and `docker-compose.hackathon.yml` comments are correct
- [ ] Test that all docker-compose files still parse correctly: `docker-compose -f docker-compose.prod.yml config`

### Organization
- [ ] Confirm archived docs under `docs/archive/` are still discoverable (or update main docs index)
- [ ] Verify `scripts/legacy/` contains only truly legacy scripts (nothing active)
- [ ] Check that root directory READMEs (`src/`, `public/`, `tests/`) are helpful for future review

### Code Quality
- [ ] Review STATUS comments in flagged scripts for accuracy
- [ ] Confirm no production scripts were accidentally moved to legacy
- [ ] Verify Prometheus/Grafana marked as legacy but still functional

### Future Planning
- [ ] Acknowledge flagged items deadline: 2025-12-31
- [ ] Note Phase 3 tasks: git history cleanup, Prometheus/Grafana decommissioning
- [ ] Confirm team is aligned on Datadog as primary observability

---

## Testing

### Pre-Merge Validation
```powershell
# 1. Verify .gitignore patterns work correctly
git status  # Should not show coverage.lcov, debug files, etc.

# 2. Test docker-compose files parse correctly
docker-compose -f docker-compose.prod.yml config > /dev/null
docker-compose -f docker-compose.hackathon.yml config > /dev/null
docker-compose -f docker-compose.edge.yml config > /dev/null

# 3. Run smoke tests to ensure no regressions
./scripts/smoke-applylens.ps1

# 4. Verify API health
./scripts/prod-health-check.ps1
```

### Post-Merge Monitoring
- Monitor production for any unexpected behavior from `.gitignore` changes
- Verify no required files are being excluded from git
- Confirm Prometheus/Grafana still accessible if needed during transition

---

## Related Documentation

- **Phase 1 Audit**: `docs/REPO_AUDIT_PHASE1.md` - Original comprehensive analysis
- **Phase 2 Summary**: `docs/REPO_CLEANUP_PHASE2_SUMMARY.md` - Detailed changes and statistics
- **Legacy Scripts**: `scripts/legacy/README.md` - Explanation of moved scripts
- **Grafana Archive**: `docs/archive/grafana/README.md` - Grafana deprecation notice
- **Phase Archive**: `docs/archive/phases/README.md` - Historical milestones
- **Datadog Setup**: `hackathon/DATADOG_SETUP.md` - Current observability stack

---

## Next Steps (Post-Merge)

### Immediate (Within 1 Week)
1. **Team review** of flagged items (ambiguous scripts, root directories)
2. **Document decisions** on `src/`, `public/`, `tests/` directories
3. **Update main README** to reference cleanup and archive structure

### Short-term (By 2025-12-31)
1. **Resolve flagged scripts** - move to legacy or document active usage
2. **Clarify docker-compose.edge.yml** - document purpose or remove
3. **Plan Prometheus/Grafana sunset** - verify Datadog has all necessary monitors

### Long-term (Phase 3 - 2026 Q1)
1. **Git history cleanup** - remove large historical artifacts (see `docs/REPO_HISTORY_CLEANUP_PLAN.md`)
2. **Prometheus/Grafana decommission** - complete migration to Datadog (see `docs/OBSERVABILITY_STACK_PLAN.md`)
3. **Final documentation consolidation** - merge overlapping guides identified in audit

---

**Branch**: `chore/repo-cleanup-phase2`
**Commit**: `d018f40`
**Files Changed**: 63 files (+1,699 insertions, -42,950 deletions)
**Pre-commit Hooks**: ✅ All passed

**Ready for review and merge.**
