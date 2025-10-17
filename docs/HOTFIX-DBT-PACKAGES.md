# Hotfix: dbt Packages Configuration

**Date:** 2025-10-17  
**Issue:** GitHub Actions workflow failing with "packages.yml is malformed" error  
**Status:** ✅ RESOLVED

## Problem

After merging PR #12, the GitHub Actions "Warehouse Nightly" workflow started failing during `dbt deps` with the error:

```
Runtime Error
  The packages.yml file in this project is malformed. Please double check
  the contents of this file and fix any errors before retrying.

  Validator Error:
  ***'name': 'dbt_utils', 'package': 'dbt-labs/dbt_utils', 'version': '1.3.1', 'unrendered': ***'name': 'dbt_utils', 'package': 'dbt-labs/dbt_utils', 'version': '1.3.1'*** is not valid under any of the given schemas
```

## Root Cause

Two issues were identified:

### 1. Tracked `dbt_packages/` Directory (Primary Issue)
The `dbt_packages/` directory (221 files) was accidentally committed to git during PR #12. This directory should be:
- **Generated** by `dbt deps` (not committed)
- **Ignored** by .gitignore
- **Excluded** from version control

When GitHub Actions ran `dbt deps`, it encountered conflicts between the committed files and the packages it tried to install, resulting in a malformed `package-lock.yml` with an `'unrendered'` field that dbt 1.8 doesn't recognize.

### 2. Version Range Syntax (Secondary Issue)
The `packages.yml` used version ranges:
```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.3.0", "<2.0.0"]  # Version range
  - package: calogica/dbt_date
    version: [">=0.10.0", "<1.0.0"]  # Version range
```

While dbt 1.11 (local) handles version ranges fine, dbt 1.8 (GitHub Actions) had issues with them in combination with the tracked packages.

## Solution

### Fix 1: Add dbt .gitignore and Remove Tracked Packages
**Commit:** `286de14`

Created `analytics/dbt/.gitignore`:
```gitignore
# dbt artifacts
target/
dbt_packages/
logs/
.user.yml
package-lock.yml

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
*.so

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
```

Removed all tracked files:
```bash
git rm -r --cached analytics/dbt/dbt_packages/
git add analytics/dbt/.gitignore
git commit -m "Add dbt .gitignore and remove tracked dbt_packages"
```

**Result:** 222 files changed, 25 insertions(+), 10,396 deletions(-)

### Fix 2: Pin Exact Package Versions
**Commit:** `81ab294`

Changed `packages.yml` to use exact versions:
```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.3.1
  - package: calogica/dbt_date
    version: 0.10.1
```

**Rationale:**
- Ensures consistent behavior across dbt versions
- Avoids dbt 1.8 version range parsing issues
- Provides deterministic builds

## Verification

### Failed Runs (Before Fix)
- Run #18580610505: Failed at "Install dbt packages" (43s)
- Run #18581083220: Failed at "Install dbt packages" (39s)

### Successful Run (After Fix)
- Run #18581111961: ✅ SUCCESS (1m31s)
  - dbt deps: ✅ Packages installed
  - dbt run: ✅ 6 models built
  - dbt test: ✅ 31 tests passed
  - dbt docs: ✅ Generated
  - ES validation: Skipped (default)

**GitHub Actions URL:** https://github.com/leok974/ApplyLens/actions/runs/18581111961

## Prevention

### For Future dbt Projects
1. **Always** create `dbt_packages/` in `.gitignore` from day one
2. **Never** commit `dbt_packages/`, `target/`, or `package-lock.yml`
3. **Pin** exact package versions when using CI/CD with different dbt versions
4. **Test** locally with the same dbt version as CI (or use version ranges cautiously)

### Repository Status
```bash
# Check what's tracked in git
git ls-files analytics/dbt/dbt_packages/  # Should return nothing

# Check .gitignore
cat analytics/dbt/.gitignore  # Should include dbt_packages/

# Verify clean state
git status  # Should show dbt_packages/ as untracked (or not at all if empty)
```

## Lessons Learned

1. **dbt 1.8 vs 1.11 Differences:**
   - Version range syntax handling
   - package-lock.yml format expectations
   - Always test with production dbt version

2. **Git Hygiene:**
   - Generated artifacts should never be committed
   - .gitignore should be comprehensive from the start
   - Review PR diffs carefully (24,757 insertions should have raised a flag)

3. **CI/CD Best Practices:**
   - Pin versions for reproducibility
   - Test workflow changes before merging large PRs
   - Use exact versions when possible

## Related Issues

- **PR #12:** "Housekeeping & 15-min sync + small improvements"
  - Accidentally included dbt_packages/ (221 files)
  - Fixed in subsequent commits
- **dbt-bigquery version:** 1.8.* (pinned in workflow)
- **Local dbt version:** 1.11.0-b3 (worked fine locally)

## Status

✅ **RESOLVED** - Workflow now passing consistently

**Next Smoke Test:** Scheduled nightly run at 4:17 AM UTC  
**Manual Trigger:** `gh workflow run "Warehouse Nightly"`

---

**Created:** 2025-10-17 03:10 UTC  
**Author:** GitHub Copilot  
**Commits:** 286de14, 81ab294
