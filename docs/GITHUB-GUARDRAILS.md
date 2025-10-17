# 🛡️ GitHub Repository Guardrails

**Purpose:** Prevent dbt artifacts and other generated files from being committed to the repository.

**Date Configured:** 2025-10-17  
**Related:** [`HISTORY-CLEANUP.md`](./HISTORY-CLEANUP.md), [`BULLETPROOFING-VERIFIED.md`](./BULLETPROOFING-VERIFIED.md)

---

## 🔒 Branch Protection Rules

### Main Branch Protection

**Navigate:** GitHub → Settings → Branches → Branch protection rules → `main`

**Required Settings:**

- ✅ **Require a pull request before merging**
  - Require approvals: 0 (solo dev) or 1+ (team)
  - Dismiss stale approvals: ✅ Enabled
  
- ✅ **Require status checks to pass before merging**
  - Require branches to be up to date: ✅ Enabled
  - **Status checks that are required:**
    - `Pre-commit Checks` - Blocks formatting/linting errors
    - `dbt Run + Validation` - Validates dbt models compile and tests pass
  
- ✅ **Require conversation resolution before merging**

- ✅ **Do not allow bypassing the above settings**
  - Include administrators: ✅ Enabled (even admins must follow rules)

- ❌ **Do not allow force pushes** (Re-enabled post-cleanup)
  - Prevents history rewrites after the 2025-10-17 cleanup

- ❌ **Do not allow deletions**

**CLI Alternative:**
```bash
gh api repos/leok974/ApplyLens/branches/main/protection -X PUT -f required_status_checks='{"strict":true,"contexts":["Pre-commit Checks","dbt Run + Validation"]}'
```

---

## 🚫 Repository Push Rulesets

**Navigate:** GitHub → Settings → Rules → Rulesets → New ruleset

### Ruleset: "Block dbt Artifacts"

**Configuration:**

| Setting | Value |
|---------|-------|
| **Ruleset Name** | Block dbt Artifacts |
| **Enforcement** | Active |
| **Bypass list** | (None - applies to everyone) |
| **Target** | All branches |

**Rules:**

1. **Block force pushes** ✅ (after cleanup complete)

2. **Restrict file paths** ✅
   - **Restricted paths (block pushes):**
     ```
     analytics/dbt/dbt_packages/**
     analytics/dbt/package-lock.yml
     analytics/dbt/target/**
     analytics/dbt/logs/**
     analytics/dbt/manifest.json
     analytics/dbt/run_results.json
     analytics/dbt/catalog.json
     ```

**Effect:**
```bash
# Attempting to push these files will fail:
$ git push origin feature-branch
remote: error: GH013: Repository rule violations found for refs/heads/feature-branch.
remote: 
remote: - DISALLOWED_FILE_PATH
remote:   Commits containing files matching the pattern 'analytics/dbt/dbt_packages/**' cannot be pushed
remote: 
remote: Review the push ruleset for this repository at:
remote: https://github.com/leok974/ApplyLens/settings/rules
```

**Manual Setup (GitHub UI):**

1. Go to https://github.com/leok974/ApplyLens/settings/rules
2. Click "New ruleset" → "New branch ruleset"
3. Name: "Block dbt Artifacts"
4. Target: "All branches"
5. Add rule: "Restrict file paths"
6. Add each path pattern above
7. Set enforcement status: "Active"
8. Click "Create"

---

## 📋 Weekly Verification

### Automated Check Script

**Location:** `analytics/ops/weekly-history-check.{sh,ps1}`

**Usage:**
```bash
# Linux/Mac
./analytics/ops/weekly-history-check.sh

# Windows
.\analytics\ops\weekly-history-check.ps1
```

**Expected Output:**
```
🔍 Weekly Git History Sanity Check
==================================

📡 Fetching latest remote refs...
🔎 Scanning remote history for dbt_packages...
🔎 Scanning remote history for package-lock.yml...

📊 Results:
  dbt_packages files:   0
  package-lock.yml:     0

✅ History is clean! No artifacts found.

📅 Last checked: 2025-10-17 00:53:46
```

**Schedule:**
- Run weekly (e.g., every Monday morning)
- Add to cron/task scheduler: `0 9 * * MON cd ~/ApplyLens && ./analytics/ops/weekly-history-check.sh`
- Or manually before monthly reviews

**Failure Response:**

If the script fails (exit code 1):
1. Identify the offending commit:
   ```bash
   git log --remotes --all -- '**/dbt_packages/**' '**/package-lock.yml'
   ```
2. Check if it's in a feature branch or PR
3. If in PR: Request changes before merge
4. If in main: Follow history cleanup procedure in [`HISTORY-CLEANUP.md`](./HISTORY-CLEANUP.md)

---

## 🎯 Complete Protection Stack

### Layer 1: Local Prevention
- ✅ Root `.gitignore` - 7 artifact patterns blocked
- ✅ Pre-commit hooks - Custom `no-dbt-artifacts` hook
- ✅ Sanity scripts - `dbt-sanity-check.{sh,ps1}`

### Layer 2: CI/CD Gates
- ✅ Pre-commit CI job - Runs ruff, formatting, artifact checks
- ✅ dbt validation job - Cleans deps, tests models
- ✅ Workflow dependency - dbt only runs if pre-commit passes

### Layer 3: GitHub Protections
- ✅ Branch protection - Requires PR + status checks
- ✅ Push rulesets - **Blocks artifact paths at server level**
- ✅ CODEOWNERS - `@leok974` review required for `analytics/dbt/**`

### Layer 4: Monitoring
- ✅ Weekly history check - Automated verification script
- ✅ Git tag anchor - `history-clean-2025-10-17` baseline

---

## 📊 Verification Commands

### Check Branch Protection Status
```bash
gh api repos/leok974/ApplyLens/branches/main/protection | jq '.required_status_checks.contexts'
# Expected: ["Pre-commit Checks", "dbt Run + Validation"]
```

### Check Push Rulesets
```bash
gh api repos/leok974/ApplyLens/rulesets | jq '.[] | {name, enforcement}'
# Expected: {"name": "Block dbt Artifacts", "enforcement": "active"}
```

### Verify No Artifacts in History
```bash
git log --remotes --format=%H | \
  xargs -I {} git ls-tree -r --name-only {} | \
  grep -E 'dbt_packages|package-lock\.yml' || echo "✅ Clean"
```

### Check Repository Size
```bash
# GitHub API (after their GC runs)
gh api repos/leok974/ApplyLens | jq .size
# Expected: ~2900 KB (down from ~3500 KB)
```

---

## 🚨 Incident Response

### Scenario 1: Artifacts Detected in PR

**Detection:** CI pre-commit job fails or code review spots files

**Response:**
1. Comment on PR: "dbt artifacts detected - please remove"
2. Author runs: `git reset HEAD analytics/dbt/{dbt_packages,package-lock.yml}`
3. Author commits: `git commit -m "Remove dbt artifacts"`
4. CI re-runs and passes

### Scenario 2: Artifacts Merged to Main

**Detection:** Weekly history check fails or manual audit

**Response:**
1. **Immediate:** Revert the merge commit
   ```bash
   git revert -m 1 <merge-commit-sha>
   git push origin main
   ```
2. **Short-term:** Add missing `.gitignore` entries
3. **Review:** Why did protections fail?
   - Pre-commit hooks not installed locally?
   - CI checks bypassed?
   - Push rulesets not configured?
4. **Follow:** History cleanup procedure if artifacts persist

### Scenario 3: Branch Protection Bypassed

**Detection:** Force-push detected or rules changed

**Response:**
1. Check audit log: GitHub → Settings → Audit log
2. Identify who bypassed and why
3. Restore protections immediately
4. Run history check to verify no artifacts added
5. Document incident and preventive measures

---

## 📅 Maintenance Schedule

### Weekly (Automated)
- ✅ Run `weekly-history-check.{sh,ps1}` script
- ✅ Review pre-commit hook auto-updates (Renovate/Dependabot)

### Monthly (Manual)
- [ ] Review GitHub audit log for protection changes
- [ ] Verify push rulesets still active
- [ ] Check CI job success rate (should be >95%)
- [ ] Update protection documentation if workflows change

### Quarterly
- [ ] Test push ruleset by attempting to push test artifact
- [ ] Review and update blocked path patterns
- [ ] Audit CODEOWNERS assignments
- [ ] Run repository size check (should stay <3 MB)

### Next Major Review
**Date:** 2026-01-14 (with Service Account key rotation)

**Tasks:**
- [ ] Verify all 10 protection layers still active
- [ ] Review incident log (any bypasses?)
- [ ] Update documentation for any workflow changes
- [ ] Test on fresh clone

---

## 🔗 Related Documentation

- [`HISTORY-CLEANUP.md`](./HISTORY-CLEANUP.md) - Complete cleanup procedure
- [`BULLETPROOFING-VERIFIED.md`](./BULLETPROOFING-VERIFIED.md) - All protection layers detailed
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) - Developer guidelines
- [`.github/workflows/dbt.yml`](../.github/workflows/dbt.yml) - CI pipeline
- [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) - Local hooks

---

## ✅ Setup Checklist

Use this when configuring a new clone or onboarding team members:

- [ ] Install pre-commit: `pip install pre-commit`
- [ ] Install hooks: `pre-commit install`
- [ ] Test hooks: `pre-commit run --all-files`
- [ ] Verify GitHub branch protection (admin only)
- [ ] Verify GitHub push rulesets (admin only)
- [ ] Schedule weekly history check (cron/task scheduler)
- [ ] Review all documentation listed above
- [ ] Test dbt workflow: `cd analytics/dbt && dbt run --target prod`

---

**🛡️ Protection Status: MAXIMUM**  
**Last Updated:** 2025-10-17  
**Next Review:** 2025-11-17 (monthly check)

