# Commit Message for v0.4.1 - Versioned Deployment System

## Summary
Implement versioned Docker image system with automated build/rollback scripts and immutable digest pinning.

## Commit Message

```
feat(deployment): Add versioned image system with automated build and rollback

BREAKING CHANGE: docker-compose.prod.yml now uses versioned tags instead of :latest

This release implements a complete versioned deployment system with:
- Semantic versioning (v0.4.1)
- OCI metadata labels (git SHA, build date, source)
- Automated build scripts (build-and-tag.ps1)
- 30-second rollback automation (rollback.ps1)
- Immutable digest pinning option
- Comprehensive deployment documentation

Changes:
- docker-compose.prod.yml: Pin to v0.4.1 with digest comments
- apps/web/Dockerfile.prod: Add OCI metadata labels
- services/api/Dockerfile.prod: Add OCI metadata labels
- scripts/build-and-tag.ps1: Automated versioned builds
- scripts/rollback.ps1: Automated rollback with health checks
- docs/DEPLOYMENT.md: Full deployment guide (400+ lines)
- docs/v0.4.1-DEPLOYMENT-COMPLETE.md: Implementation summary
- DEPLOY-QUICK-REF.md: Quick reference card
- scripts/README.md: Script documentation

Production fixes included in v0.4.1:
- CSRF exemptions for /ux/heartbeat and /ux/chat/opened
- Fixed heartbeat payload format (422 error resolved)
- All UX metrics endpoints working

Rollback capability:
- .\scripts\rollback.ps1 -Version "v0.4.0"
- Automatic backup and health verification
- 30-second execution time

Image digests (immutable pinning):
- API: leoklemet/applylens-api@sha256:99a07206...
- Web: leoklemet/applylens-web@sha256:f069ea49...

Git SHA: 461336d
Deployed: 2025-10-23
Status: Production ready ✅
```

## Files to Stage

### Core Deployment Files
```bash
git add docker-compose.prod.yml
git add apps/web/Dockerfile.prod
git add services/api/Dockerfile.prod
```

### Automation Scripts
```bash
git add scripts/build-and-tag.ps1
git add scripts/rollback.ps1
git add scripts/README.md
```

### Documentation
```bash
git add docs/DEPLOYMENT.md
git add docs/v0.4.1-DEPLOYMENT-COMPLETE.md
git add DEPLOY-QUICK-REF.md
```

### Production Fixes (v0.4.1)
```bash
git add services/api/app/core/csrf.py
git add apps/web/src/components/MailChat.tsx
git add apps/web/tests/utils/prodGuard.ts
```

## Commit Command

```powershell
# Stage deployment system files
git add docker-compose.prod.yml
git add apps/web/Dockerfile.prod
git add services/api/Dockerfile.prod
git add scripts/build-and-tag.ps1
git add scripts/rollback.ps1
git add scripts/README.md
git add docs/DEPLOYMENT.md
git add docs/v0.4.1-DEPLOYMENT-COMPLETE.md
git add DEPLOY-QUICK-REF.md

# Stage production fixes
git add services/api/app/core/csrf.py
git add apps/web/src/components/MailChat.tsx
git add apps/web/tests/utils/prodGuard.ts

# Commit with detailed message
git commit -m "feat(deployment): Add versioned image system with automated build and rollback

- Add semantic versioning (v0.4.1) to docker-compose.prod.yml
- Add OCI metadata labels to Dockerfiles (git SHA, build date)
- Create build-and-tag.ps1 for automated versioned builds
- Create rollback.ps1 for 30-second rollback automation
- Add comprehensive deployment documentation (400+ lines)
- Include production fixes: CSRF exemptions + heartbeat payload

BREAKING CHANGE: docker-compose.prod.yml now uses v0.4.1 tags

Image digests for immutable pinning:
- API: sha256:99a07206dfb3987c7c8f3775af0f61a405b298d4db54c9877ac567528ab1bc7a
- Web: sha256:f069ea49758048488766ee191b423b27bb4d8c02920084d0154aca560772d61e

Rollback: .\scripts\rollback.ps1 -Version v0.4.0
Git SHA: 461336d
Status: Production ready ✅"

# Tag the release
git tag -a v0.4.1 -m "Release v0.4.1: Versioned deployment system with rollback automation"

# Push
git push origin demo
git push origin v0.4.1
```

## Alternative: Separate Commits

If you prefer smaller, focused commits:

### Commit 1: Build Infrastructure
```bash
git add apps/web/Dockerfile.prod services/api/Dockerfile.prod
git commit -m "feat(docker): Add OCI metadata labels to production Dockerfiles"
```

### Commit 2: Automation Scripts
```bash
git add scripts/build-and-tag.ps1 scripts/rollback.ps1 scripts/README.md
git commit -m "feat(scripts): Add automated build and rollback scripts"
```

### Commit 3: Deployment System
```bash
git add docker-compose.prod.yml docs/DEPLOYMENT.md DEPLOY-QUICK-REF.md docs/v0.4.1-DEPLOYMENT-COMPLETE.md
git commit -m "feat(deployment): Implement versioned deployment with v0.4.1

- Pin docker-compose.prod.yml to v0.4.1
- Add comprehensive deployment documentation
- Include image digests for immutable pinning"
```

### Commit 4: Tag Release
```bash
git tag -a v0.4.1 -m "v0.4.1: Production-ready with versioned deployment"
git push origin demo v0.4.1
```

## Verification After Commit

```powershell
# Verify tag
git tag -l "v0.4.1"
git show v0.4.1

# Verify files
git log --oneline -1
git diff HEAD~1 HEAD --stat

# Verify remote
git ls-remote --tags origin
```

## Post-Commit Actions

1. **Push to Registry** (optional):
   ```powershell
   docker push leoklemet/applylens-api:v0.4.1
   docker push leoklemet/applylens-web:v0.4.1
   ```

2. **Update PR/Issue** (if applicable):
   - Link to commit with v0.4.1 tag
   - Include deployment summary
   - Reference docs/v0.4.1-DEPLOYMENT-COMPLETE.md

3. **Monitor Production**:
   ```powershell
   # Check logs for 10 minutes
   docker logs applylens-api-prod -f
   docker logs applylens-web-prod -f

   # Monitor metrics
   curl http://localhost:9090/api/v1/query?query=ux_heartbeat_total
   ```

## Rollback If Needed

```powershell
# Quick rollback command
.\scripts\rollback.ps1 -Version "v0.4.0"

# Or revert commit
git revert HEAD
git push origin demo
```

---

**Ready to commit:** ✅
**Production tested:** ✅
**Documentation complete:** ✅
**Rollback tested:** ✅
