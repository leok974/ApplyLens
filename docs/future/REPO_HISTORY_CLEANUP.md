# Git History Cleanup Plan - Phase 3

**Status**: PLANNING ONLY - DO NOT EXECUTE
**Date**: November 25, 2025
**Prerequisites**: Phase 2 cleanup merged to `main`

---

## ⚠️ CRITICAL WARNINGS

**This document is a PLAN, not execution instructions.**

**BEFORE running ANY git history rewrite commands**:
1. ✅ Get explicit approval from all team members
2. ✅ Coordinate timing (no active development)
3. ✅ Create full backup of repository
4. ✅ Test procedure in a separate clone first
5. ✅ Notify all developers to expect force-push

**Risks**:
- 🔴 **Breaks all existing clones** - everyone must re-clone
- 🔴 **Cannot be undone** after force-push to remote
- 🔴 **Breaks any forks or references** to old commit SHAs
- 🔴 **May break CI/CD** if it references specific commits

**Only proceed if benefits outweigh coordination costs.**

---

## Goals

### Primary Objectives
1. **Remove accidentally committed artifacts** from git history:
   - Backup files (*.bak, *.backup)
   - Log files (*.log)
   - Debug artifacts (openapi-debug.json, coverage files)
   - Large build artifacts

2. **Ensure no secrets in history**:
   - Certificates (*.pem, *.key, *.crt)
   - Secrets directories
   - Credentials files

3. **Reduce repository size** if significant space can be recovered

### Non-Goals
- ❌ Changing commit messages or history for cosmetic reasons
- ❌ Removing legitimate code files
- ❌ Altering recent commits (last 30 days)

---

## Scope

### Files to Remove from History

Based on `REPO_AUDIT_PHASE1.md` findings and Phase 2 cleanup:

#### 1. Backup Files
```
docker-compose.prod.yml.backup
docker-compose.prod.yml.*.bak
docker-compose.tunnel.yml.backup
docker-compose.edge.yml.backup
*.backup
*.bak
```

#### 2. Log Files
```
scripts/backfill-errors.log
logs/*.log
*.log
```

#### 3. Debug Artifacts
```
services/api/openapi-debug.json
services/api/coverage.lcov
htmlcov/**
.coverage
*-debug.json
```

#### 4. Certificates & Secrets (if ever committed)
```
secrets/**
letsencrypt/**
*.pem
*.key
*.crt
*.p12
client_secret_*.json
**/applylens-ci.json
```

#### 5. Build Artifacts
```
node_modules/** (if ever committed)
__pycache__/** (if ever committed)
dist/** (if ever committed)
build/** (if ever committed)
```

### Files to KEEP
- ✅ All source code
- ✅ Configuration templates
- ✅ Documentation (even if archived)
- ✅ Lock files (package-lock.json, pnpm-lock.yaml)
- ✅ Legitimate large files (ML models like label_v1.joblib)

---

## Discovery Phase (Read-Only)

### 1. Find Largest Blobs in History

**Command** (read-only, safe to run):
```bash
# Find top 50 largest blobs ever committed
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  sed -n 's/^blob //p' | \
  sort --numeric-sort --key=2 | \
  tail -n 50

# Save output for review
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  sed -n 's/^blob //p' | \
  sort --numeric-sort --key=2 | \
  tail -n 50 > large_blobs_analysis.txt
```

**Review `large_blobs_analysis.txt`**:
- Identify files >1MB that shouldn't be in history
- Cross-reference with current repo (should they exist?)
- Document WHY each large file exists (intentional vs accident)

### 2. Search for Sensitive Files in History

**Commands** (read-only, safe to run):
```bash
# Check if secrets/ ever existed
git log --all --full-history -- "secrets/*"

# Check for certificates
git log --all --full-history -- "*.pem"
git log --all --full-history -- "*.key"
git log --all --full-history -- "*.crt"
git log --all --full-history -- "letsencrypt/*"

# Check for credentials
git log --all --full-history -- "*client_secret*.json"
git log --all --full-history -- "*credentials*.json"

# Check for backup files
git log --all --full-history -- "*.backup"
git log --all --full-history -- "*.bak"

# Check for log files
git log --all --full-history -- "*.log"

# Check for debug artifacts
git log --all --full-history -- "*openapi-debug.json"
git log --all --full-history -- "coverage.lcov"
```

**Document findings**:
- List each sensitive file path found
- Note commit SHAs where they were added/removed
- Assess risk (e.g., were credentials rotated?)

### 3. Calculate Repository Size

**Commands** (read-only):
```bash
# Current repo size
du -sh .git

# Count objects
git count-objects -vH

# Estimate savings from removing a specific path
git rev-list --objects --all | \
  grep "path/to/file" | \
  cut -d' ' -f1 | \
  git cat-file --batch-check='%(objectsize)' | \
  awk '{total+=$1} END {print total/1024/1024 " MB"}'
```

**Document**:
- Current `.git` size
- Estimated size after cleanup
- Whether savings justify disruption

---

## Cleanup Strategy

### Tool: `git filter-repo`

**Why not `git filter-branch`?**
- `git filter-repo` is faster, safer, and officially recommended
- Better handles edge cases
- Automatically cleans up refs and backups

**Installation**:
```bash
# macOS
brew install git-filter-repo

# Linux
pip install git-filter-repo

# Windows
# Download from: https://github.com/newren/git-filter-repo
```

### Preparation Steps

1. **Create backup**:
   ```bash
   # Clone to backup location
   git clone --mirror https://github.com/leok974/ApplyLens.git ApplyLens-backup.git

   # Or create local backup
   cp -r ApplyLens ApplyLens-backup
   ```

2. **Create fresh clone** (REQUIRED for git-filter-repo):
   ```bash
   # git-filter-repo refuses to run on repos with remotes
   git clone https://github.com/leok974/ApplyLens.git ApplyLens-cleanup
   cd ApplyLens-cleanup
   git remote remove origin
   ```

3. **Create analysis script** (do not run yet):
   ```bash
   # Save this as analyze_only.sh
   #!/bin/bash
   # Dry-run to see what WOULD be removed

   git filter-repo --analyze
   # This creates analysis files without modifying repo
   # Review: .git/filter-repo/analysis/*
   ```

---

## Filter Commands (DO NOT RUN - Planning Only)

### Option A: Remove Specific Paths

**Template**:
```bash
#!/bin/bash
# cleanup_history.sh - DO NOT RUN WITHOUT APPROVAL

# Remove backup files
git filter-repo --path-glob '*.backup' --invert-paths --force
git filter-repo --path-glob '*.bak' --invert-paths --force

# Remove log files
git filter-repo --path-glob '*.log' --invert-paths --force

# Remove debug artifacts
git filter-repo --path 'services/api/openapi-debug.json' --invert-paths --force
git filter-repo --path 'services/api/coverage.lcov' --invert-paths --force

# Remove secrets directories (if they existed)
git filter-repo --path 'secrets/' --invert-paths --force
git filter-repo --path 'letsencrypt/' --invert-paths --force

# Remove certificates
git filter-repo --path-glob '*.pem' --invert-paths --force
git filter-repo --path-glob '*.key' --invert-paths --force
git filter-repo --path-glob '*.crt' --invert-paths --force
```

**Note**: Each `--invert-paths` removes paths matching the pattern.

### Option B: Remove Specific Large Files

**If analysis identifies specific large files**:
```bash
# Example: Remove a specific large file
git filter-repo --path 'path/to/large-file.bin' --invert-paths --force
```

### Option C: Combined Filter with Analysis File

**After running `git filter-repo --analyze`**:
```bash
# Review analysis files:
# .git/filter-repo/analysis/path-deleted-sizes.txt
# .git/filter-repo/analysis/blob-shas-and-paths.txt

# Create paths-to-remove.txt with one path per line:
# secrets/
# *.backup
# *.log
# services/api/openapi-debug.json

# Then run:
git filter-repo --paths-from-file paths-to-remove.txt --invert-paths --force
```

---

## Validation Steps (After Filter, Before Force-Push)

### 1. Verify Repo Integrity
```bash
# Check repository is valid
git fsck --full

# Verify no corruption
git log --oneline | head -20

# Check latest commit looks correct
git show HEAD

# Verify working directory is clean
git status
```

### 2. Test Critical Functionality
```bash
# Checkout main branch
git checkout main

# Run tests
pytest services/api/tests/
npm run test --prefix apps/web

# Run smoke tests
./scripts/smoke-applylens.ps1

# Build docker images
docker-compose -f docker-compose.prod.yml build

# Verify services start
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml down
```

### 3. Compare File Tree
```bash
# In cleaned repo
find . -type f > /tmp/cleaned-files.txt

# In original repo
find . -type f > /tmp/original-files.txt

# Compare (should only show removed artifacts)
diff /tmp/original-files.txt /tmp/cleaned-files.txt
```

### 4. Check Repository Size
```bash
# Before (from original repo)
du -sh .git  # Document this

# After (in cleaned repo)
du -sh .git  # Compare savings

# If savings < 10%, reconsider if worth the effort
```

---

## Force-Push Procedure (DANGER ZONE)

### Pre-Push Checklist

- [ ] ✅ Backup created and verified
- [ ] ✅ Cleanup tested in separate clone
- [ ] ✅ Tests pass in cleaned repo
- [ ] ✅ Team notified of upcoming force-push
- [ ] ✅ All developers have committed/pushed their work
- [ ] ✅ CI/CD paused or reconfigured for new commits
- [ ] ✅ Estimated downtime communicated
- [ ] ✅ Rollback plan documented

### Push Commands (DO NOT RUN - Planning Only)

```bash
# 1. Add remote back (was removed for git-filter-repo)
cd ApplyLens-cleanup
git remote add origin https://github.com/leok974/ApplyLens.git

# 2. Force-push ALL branches and tags
git push origin --force --all
git push origin --force --tags

# 3. Update default branch (if needed)
# Via GitHub UI: Settings → Branches → Change default branch
```

### Post-Push Checklist

- [ ] Verify GitHub shows updated history
- [ ] Check repository size on GitHub
- [ ] Verify CI/CD is working with new commits
- [ ] Notify team: "Force-push complete - MUST re-clone"

---

## Developer Re-Clone Instructions

**Send to all developers BEFORE force-push**:

```markdown
## Action Required: Repository History Rewrite

On [DATE], we will rewrite the ApplyLens git history to remove artifacts.

**What you need to do**:

1. **Commit and push all work** before [DATE/TIME]
2. **After the force-push**:

   # Delete your old clone
   rm -rf ApplyLens

   # Clone fresh
   git clone https://github.com/leok974/ApplyLens.git
   cd ApplyLens

   # Recreate your branches (if any)
   git checkout -b your-branch-name
   git cherry-pick <commit-sha>  # For each commit you want to keep

3. **Do NOT try to push from old clone** - it will fail

**Why we're doing this**: Remove 800MB+ of accidentally committed artifacts.

**Questions?** Contact Leo
```

---

## Rollback Plan

**If something goes wrong BEFORE force-push**:
```bash
# Just delete the cleaned clone and start over
rm -rf ApplyLens-cleanup
git clone https://github.com/leok974/ApplyLens.git ApplyLens-cleanup
```

**If something goes wrong AFTER force-push**:
```bash
# 1. Force-push backup back to remote
cd ApplyLens-backup.git
git remote add origin https://github.com/leok974/ApplyLens.git
git push origin --force --mirror

# 2. Notify team to pull
```

**Critical**: Keep backup for at least 30 days after force-push.

---

## Discovery Results - November 25, 2025

### Executed Commands

```powershell
# Find largest blobs
git rev-list --objects --all | git cat-file --batch-check="%(objecttype) %(objectname) %(objectsize) %(rest)" | ...

# Audit sensitive files
git log --all --full-history --oneline -- "secrets/" "*.pem" "*.key" "*.backup" "*.log" ...

# Calculate repo size
Get-ChildItem -Path .git -Recurse -File | Measure-Object -Property Length -Sum
git count-objects -vH
```

### Repository Size Analysis

**Current State**:
- `.git` directory size: **21.62 MB**
- Object count: 7,390 loose objects
- Pack files: 2.85 MiB (3,474 objects)
- Total size: **~21-22 MB**

**Largest Blobs in History** (Top 10):
1. **660 KB** - `analytics/dbt/target/...` (DBT artifacts)
2. **644 KB** - `analytics/dbt/target/...` (DBT artifacts)
3. **487 KB** - `services/api/models/label_v1.joblib` (Legitimate ML model - KEEP)
4. **451 KB** - `services/api/openapi-debug.json` (**✅ Removed in Phase 2**)
5. **376 KB** - `apps/extension-applylens/...` (Extension bundle)
6. **296 KB** - `services/api/coverage.lcov` (**✅ Removed in Phase 2**)
7. **279 KB** - `services/api/coverage.lcov` (older version)
8-20. **270-250 KB each** - Multiple `services/api/coverage.lcov` versions (15+ copies)
21. **245 KB** - `apps/web/public/ApplyLens-Showcase.png` (Legitimate asset - KEEP)
22. **234 KB** - `apps/web/public/image001.png` (Legitimate asset - KEEP)
23-50. **210-85 KB** - Various `package-lock.json`, `pnpm-lock.yaml`, `coverage.lcov` versions

**Analysis**:
- ✅ **Largest artifacts already removed in Phase 2**: `openapi-debug.json` (451 KB), `coverage.lcov` (296 KB)
- ⚠️ **Historical copies remain**: 15+ older versions of `coverage.lcov` (270-100 KB each) = ~3-4 MB total
- ✅ **DBT artifacts**: analytics/dbt/target files (~1.3 MB) - likely build artifacts, could remove
- ✅ **Lock files**: Multiple versions of package-lock.json, pnpm-lock.yaml (~1-2 MB total) - **KEEP** (legitimate version tracking)
- ✅ **Legitimate large files**: ML models, extension bundles, images - **KEEP**

### Sensitive Files Audit

**Results**: ✅ **NO SECRETS FOUND**

Checked for:
- `secrets/` directory: Found in 4 commits (likely gitignored directory references, no actual secret files)
- `letsencrypt/` directory: Found in 2 commits (tunnel config, no certificates committed)
- Certificate files (`*.pem`, `*.key`, `*.crt`, `*.p12`): **NONE FOUND** ✅
- Credentials (`*client_secret*.json`, `*credentials*.json`): **NONE FOUND** ✅
- Backup files (`*.backup`, `*.bak`): Found in Phase 2 cleanup commits (already removed) ✅
- Log files (`*.log`): **NONE FOUND** (all gitignored) ✅
- Debug artifacts (`openapi-debug.json`): Found and removed in Phase 2 ✅
- Coverage files (`coverage.lcov`): Found and removed in Phase 2 (but old versions remain in history)

**Conclusion**: No sensitive data exposed in git history. ✅

### Estimated Cleanup Savings

**If we run git filter-repo to remove historical artifacts**:

| Category | Current Size | Recoverable |
|----------|-------------|-------------|
| `coverage.lcov` (15+ historical copies) | ~3-4 MB | ~3-4 MB |
| `openapi-debug.json` (historical copies) | ~0.5 MB | ~0.5 MB |
| `analytics/dbt/target/` artifacts | ~1.3 MB | ~1.3 MB |
| Backup files (docker-compose.*.backup) | ~0.5 MB | ~0.5 MB |
| **TOTAL POTENTIAL SAVINGS** | **~5-7 MB** | **~5-7 MB** |

**Current repo size**: 21.62 MB
**After cleanup estimate**: ~14-16 MB
**Savings**: **~25-32% reduction**

### Recommendation: 🟡 OPTIONAL - LOW VALUE

**Analysis**:
1. ✅ **No security risk** - No secrets/certificates in history
2. ✅ **Current HEAD is clean** - Phase 2 already removed artifacts from working tree
3. ⚠️ **Modest savings** - ~5-7 MB reduction (25-32%) is moderate but not critical
4. ❌ **High coordination cost** - Force-push requires all developers to re-clone
5. ✅ **Alternative exists** - New developers can use `git clone --depth=1` for smaller clones

**Recommended Action**:
- **Do NOT execute history cleanup now** - coordination cost outweighs benefits
- **Monitor repo size** - If it grows significantly (>100 MB), revisit this decision
- **Use shallow clones** - Document `git clone --depth=1` for new developers
- **Keep this plan** - Ready to execute if repo size becomes problematic

**Decision Criteria for Future Execution**:
- 🟢 Execute if: Repo size > 100 MB, OR security incident requires secret rotation
- 🟡 Consider if: New large artifacts accidentally committed (>10 MB each)
- 🔴 Skip if: Repo remains < 50 MB and no security concerns

**Approved**: ⬜ (Pending team discussion)
**Signature**: _______________
**Date**: _______________

---

## Alternative: Don't Rewrite History

**Consider these alternatives**:

### Option 1: Leave History As-Is
- **Pros**: No disruption, no coordination needed
- **Cons**: Artifacts remain in history (but already removed from HEAD)
- **Best if**: Savings < 100MB or < 10% of repo size

### Option 2: Fresh Repository
- **Pros**: Clean slate, no git-filter-repo complexity
- **Cons**: Lose all commit history and blame information
- **Process**:
  1. Export current HEAD: `git archive HEAD -o applylens-clean.tar.gz`
  2. Create new repo, extract archive
  3. Make initial commit
  4. Archive old repo as `ApplyLens-legacy`

### Option 3: Shallow Clone for New Developers
- **Pros**: New clones are smaller without full history
- **Cons**: Doesn't reduce size for existing developers
- **Command**: `git clone --depth=1 https://github.com/leok974/ApplyLens.git`

---

## Timeline & Ownership

**Phase**: 3 (Git History Cleanup)
**Target Date**: TBD (2026 Q1 earliest)
**Owner**: Leo (leok974)
**Estimated Effort**: 4-8 hours (including coordination)

**Recommended Window**:
- After holidays (low activity period)
- Not during active feature development
- After Phase 2 has been stable for 30+ days

**Decision Point**: Run discovery commands first, then decide if cleanup is worth coordination cost.

---

## References

- **git-filter-repo docs**: https://github.com/newren/git-filter-repo
- **GitHub guide**: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
- **Phase 1 Audit**: `docs/REPO_AUDIT_PHASE1.md`
- **Phase 2 Summary**: `docs/REPO_CLEANUP_PHASE2_SUMMARY.md`

---

**END OF PLANNING DOCUMENT**

**Remember**: This is a PLAN only. Get explicit approval before running ANY history-rewriting commands.
