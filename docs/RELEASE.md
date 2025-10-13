# Release Process

This document outlines the versioning strategy, release workflow, and PR checklist for ApplyLens.

## Versioning

ApplyLens follows **Semantic Versioning 2.0.0** (<https://semver.org/>):

```text
MAJOR.MINOR.PATCH

Example: 1.2.3
```text

- **MAJOR:** Breaking changes (API changes, database schema incompatibilities)
- **MINOR:** New features (backwards-compatible)
- **PATCH:** Bug fixes (backwards-compatible)

### Pre-release Tags

- **Alpha:** `1.0.0-alpha.1` (early development, unstable)
- **Beta:** `1.0.0-beta.1` (feature-complete, testing)
- **RC:** `1.0.0-rc.1` (release candidate, final testing)

## Branch Strategy

### Main Branches

- **`main`** - Production-ready code
- **`develop`** - Integration branch for features

### Supporting Branches

- **`feature/*`** - New features (e.g., `feature/email-search`)
- **`bugfix/*`** - Bug fixes (e.g., `bugfix/oauth-refresh`)
- **`hotfix/*`** - Critical production fixes
- **`release/*`** - Release preparation (e.g., `release/1.2.0`)
- **`polish/*`** - UI/UX improvements
- **`phase-*`** - Major project phases

### Workflow

```bash
1. Create feature branch from develop
   git checkout -b feature/my-feature develop

2. Commit changes
   git commit -m "feat: add email search"

3. Push and create PR to develop
   git push origin feature/my-feature

4. After review, merge to develop

5. For release:
   git checkout -b release/1.2.0 develop
   # Update version, changelog
   git merge --no-ff release/1.2.0 main
   git tag -a v1.2.0 -m "Release 1.2.0"
```text

## Commit Message Convention

Follow **Conventional Commits** (<https://www.conventionalcommits.org/>):

```text
<type>(<scope>): <subject>

[optional body]

[optional footer]
```text

### Types

- **feat:** New feature
- **fix:** Bug fix
- **docs:** Documentation changes
- **style:** Code formatting (no logic changes)
- **refactor:** Code restructuring (no behavior change)
- **test:** Add or update tests
- **chore:** Build, dependencies, tooling

### Examples

```bash
feat(search): add full-text search with Elasticsearch

Implemented multi-field search across subject and body.
Added faceted filters for category and sender domain.

Closes #123

---

fix(oauth): refresh token expiration handling

Handle 401 errors by refreshing access token using refresh token.
Retry failed requests after token refresh.

---

docs(readme): update installation instructions

Added Docker Compose setup steps and environment variable configuration.

---

test(emails): add test for risk score calculation

Added unit tests for confidence learning risk scoring.
Covered edge cases: empty features, negative weights.
```text

## Release Checklist

### Pre-Release

- [ ] All tests passing (pytest, Playwright E2E)
- [ ] Code coverage ≥ 80%
- [ ] No critical or high-severity vulnerabilities (`npm audit`, `pip-audit`)
- [ ] Documentation updated (README, CHANGELOG, API docs)
- [ ] Database migrations tested (upgrade + downgrade)
- [ ] Environment variables documented in `.env.example`
- [ ] Breaking changes documented in CHANGELOG

### Version Bump

- [ ] Update `package.json` version (root + `services/web`)
- [ ] Update `pyproject.toml` or `__version__` in Python
- [ ] Update `CHANGELOG.md` with release notes
- [ ] Create release branch: `git checkout -b release/X.Y.Z develop`

### Testing

- [ ] Run full test suite: `make test-all`
- [ ] Manual smoke tests:
  - [ ] Login/logout flow
  - [ ] Email sync from Gmail
  - [ ] Search and filters
  - [ ] Application tracker CRUD
  - [ ] Security policy creation
  - [ ] Risk score calculation
- [ ] Load testing (if significant changes)
- [ ] Browser compatibility (Chrome, Firefox, Safari)

### Deployment

- [ ] Merge release branch to `main`
- [ ] Tag release: `git tag -a vX.Y.Z -m "Release X.Y.Z"`
- [ ] Push tags: `git push origin vX.Y.Z`
- [ ] Deploy to staging environment
- [ ] Run smoke tests on staging
- [ ] Deploy to production
- [ ] Monitor logs and metrics (Grafana)

### Post-Release

- [ ] Merge `main` back to `develop`
- [ ] Create GitHub release with notes
- [ ] Announce release (if applicable)
- [ ] Close related issues/PRs
- [ ] Update project board

## Pull Request Template

Create `.github/pull_request_template.md`:

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Related Issues

Closes #(issue)

## Changes Made

- Change 1
- Change 2
- Change 3

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

**Test Steps:**
1. Step 1
2. Step 2
3. Expected result

## Checklist

- [ ] Code follows style guidelines (ruff, black, ESLint)
- [ ] Self-review performed
- [ ] Comments added to complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally
- [ ] Dependent changes merged

## Screenshots (if applicable)

Before: [image]
After: [image]
```text

## Hotfix Process

For critical production bugs:

```bash
# 1. Create hotfix branch from main
git checkout -b hotfix/critical-bug main

# 2. Fix the bug
git commit -m "fix: critical bug description"

# 3. Bump patch version
# Update version in package.json, CHANGELOG.md

# 4. Merge to main
git checkout main
git merge --no-ff hotfix/critical-bug

# 5. Tag release
git tag -a v1.2.1 -m "Hotfix 1.2.1"

# 6. Merge to develop
git checkout develop
git merge --no-ff hotfix/critical-bug

# 7. Deploy immediately
git push origin main develop --tags
```text

## Changelog Format

Use [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
# Changelog

## [Unreleased]

### Added
- New feature X

### Changed
- Modified behavior Y

### Deprecated
- Feature Z will be removed in v2.0.0

### Removed
- Removed deprecated API endpoint

### Fixed
- Fixed bug in risk score calculation

### Security
- Fixed SQL injection vulnerability

## [1.2.0] - 2025-10-13

### Added
- Full-text email search with Elasticsearch
- Faceted filters for category and sender domain
- Application tracker pagination

### Fixed
- OAuth refresh token expiration handling
- Email sync race condition

## [1.1.0] - 2025-09-15

...
```text

## Automated Release (GitHub Actions)

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Extract version
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT
      
      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ steps.version.outputs.VERSION }}
          body_path: ./CHANGELOG.md
          draft: false
          prerelease: false
      
      - name: Build Docker images
        run: |
          docker build -t applylens/api:${{ steps.version.outputs.VERSION }} services/api
          docker build -t applylens/web:${{ steps.version.outputs.VERSION }} services/web
      
      - name: Push Docker images
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push applylens/api:${{ steps.version.outputs.VERSION }}
          docker push applylens/web:${{ steps.version.outputs.VERSION }}
```text

## See Also

- [CHANGELOG.md](./CHANGELOG.md)
- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [Operations Guide](./OPS.md)
