# GitHub Repository Ruleset Setup

This document provides instructions for setting up the GitHub repository ruleset to protect sensitive documentation.

## Overview

Configure a repository ruleset to require PR reviews for changes to documentation files that may contain sensitive information.

## Ruleset Configuration

### Navigate to Ruleset Settings

1. Go to: `https://github.com/leok974/ApplyLens/settings/rules`
2. Click **"New branch ruleset"** or **"New tag ruleset"** → Choose **Branch ruleset**

### Ruleset: "Docs Secret Protection"

**General Settings:**
- **Name**: `Docs Secret Protection`
- **Enforcement status**: Active
- **Bypass list**: 
  - Repository administrators (optional, use with caution)
  - Specific users/teams if needed

**Target branches:**
- Target: `Include by pattern`
- Pattern: `main`, `develop`

**Rules:**

1. **Require a pull request before merging**
   - ✅ Enable
   - Required approvals: `1`
   - ✅ Dismiss stale pull request approvals when new commits are pushed
   - ✅ Require review from Code Owners (optional)

2. **Require status checks to pass**
   - ✅ Enable
   - Required checks:
     - `gitleaks` (from secret-scan.yml workflow)
     - `secret-policy-check` (from secret-scan.yml workflow)
   - ✅ Require branches to be up to date before merging

3. **Block force pushes**
   - ✅ Enable

4. **Restrict file paths** (if available)
   - Target paths: `docs/**`
   - Block commits that add/modify files matching patterns:
     - `*Authorization:*`
     - `*Bearer *`
     - `*eyJr*` (Base64 Grafana keys)
     - `*ghp_*` (GitHub PAT)
     - `*AKIA*` (AWS keys)
     - `*sk-*` (OpenAI keys)

## Alternative: Branch Protection Rules

If rulesets are not available, use traditional branch protection:

1. Go to: `https://github.com/leok974/ApplyLens/settings/branches`
2. Add rule for `main` branch:
   - ✅ Require pull request reviews before merging (1 approval)
   - ✅ Require status checks to pass before merging
     - Add: `gitleaks`, `secret-policy-check`
   - ✅ Require branches to be up to date before merging
   - ✅ Do not allow bypassing the above settings

## CODEOWNERS Setup

Create `.github/CODEOWNERS` to require specific reviewers for sensitive paths:

```bash
# Require review for all documentation changes
docs/** @leok974

# Require review for configuration files
*.yml @leok974
*.toml @leok974
.env.example @leok974
```

**To create CODEOWNERS:**

```bash
# Create file
cat > .github/CODEOWNERS << 'EOF'
# Documentation requires review
docs/** @leok974

# Configuration files require review
*.yml @leok974
*.toml @leok974
.env.example @leok974

# Secrets scanning configuration requires review
.gitleaks.toml @leok974
.pre-commit-config.yaml @leok974
EOF

# Commit and push
git add .github/CODEOWNERS
git commit -m "chore: Add CODEOWNERS for sensitive files"
git push origin main
```

## Verification

After setting up rulesets:

1. **Test PR requirement:**
   ```bash
   # Try to push directly (should fail if enforced)
   git checkout -b test-branch
   echo "test" >> docs/test.md
   git add docs/test.md
   git commit -m "test: verify ruleset"
   git push origin test-branch
   
   # Create PR via GitHub UI - should require approval
   ```

2. **Test secret scanning:**
   ```bash
   # Add a fake secret
   echo "api_key = 'ghp_1234567890123456789012345678901234'" >> test.py
   git add test.py
   git commit -m "test: trigger secret scan"
   git push origin test-branch
   
   # Check that CI fails and blocks merge
   ```

3. **Test status checks:**
   - Create a PR
   - Verify that `gitleaks` and `secret-policy-check` workflows run
   - Verify that PR cannot be merged until checks pass

## Monitoring

- **Code Scanning Alerts**: `https://github.com/leok974/ApplyLens/security/code-scanning`
- **Secret Scanning Alerts**: `https://github.com/leok974/ApplyLens/security/secret-scanning`
- **Actions Workflows**: `https://github.com/leok974/ApplyLens/actions`

## Troubleshooting

### Ruleset not enforcing

- Check enforcement status is "Active"
- Verify target branches include your working branch
- Ensure required status checks match workflow job names exactly

### Status checks not appearing

- Push at least one commit to trigger workflows
- Check `.github/workflows/secret-scan.yml` is on target branch
- Verify workflow has `pull_request` trigger

### False positives in secret scanning

- Update `.gitleaks.toml` allowlist
- Add paths to exclude in `[allowlist.paths]`
- Add regex patterns to `[allowlist.regexes]`
- Regenerate baseline: `gitleaks detect --source . --baseline-path .gitleaks.baseline --report-format json --report-path .gitleaks.baseline`

## References

- [GitHub Rulesets Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [CODEOWNERS Syntax](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [Required Status Checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)

---

**Last Updated**: 2025-01-XX  
**Author**: ApplyLens Team  
**Status**: Implementation Guide
