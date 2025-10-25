# ApplyLens Deployment Scripts

Automation scripts for building, deploying, and rolling back ApplyLens Docker images.

## Scripts

### 🔨 build-and-tag.ps1
Build and tag Docker images with proper versioning and metadata.

**Usage:**
```powershell
# Build both API and Web
.\scripts\build-and-tag.ps1 -Version "v0.4.2"

# Build and push to registry
.\scripts\build-and-tag.ps1 -Version "v0.4.2" -Push

# Build only specific service
.\scripts\build-and-tag.ps1 -Version "v0.4.2" -SkipApi   # Web only
.\scripts\build-and-tag.ps1 -Version "v0.4.2" -SkipWeb   # API only
```

**Features:**
- Automatically adds Git SHA and build timestamp
- Tags with both version and `:latest`
- Shows digests for immutable pinning
- Optional registry push
- Color-coded output

**Output:**
- Built images tagged with version and `:latest`
- OCI metadata labels (git SHA, build date, source URL)
- Image digests for docker-compose pinning

---

### ⏪ rollback.ps1
Rollback to a previous version with automatic backup.

**Usage:**
```powershell
# Rollback both services
.\scripts\rollback.ps1 -Version "v0.4.0"

# Rollback specific service
.\scripts\rollback.ps1 -Version "v0.4.0" -Service "api"
.\scripts\rollback.ps1 -Version "v0.4.0" -Service "web"
.\scripts\rollback.ps1 -Version "v0.4.0" -Service "both"

# Dry run (preview changes without executing)
.\scripts\rollback.ps1 -Version "v0.4.0" -DryRun
```

**Features:**
- Automatic backup of docker-compose.prod.yml
- Pulls missing images from registry
- Updates compose file with target version
- Recreates containers
- Verifies health checks
- Auto-rollback on failure
- Dry-run mode for safety

**Safety:**
- Creates timestamped backups
- Validates images before rollback
- Tests health endpoints after rollback
- Reverts to backup if verification fails

---

## Prerequisites

- Docker Desktop installed and running
- PowerShell 7+ (comes with Windows 11)
- Git repository checked out
- Access to registry (for push operations)

## Workflow Example

### Standard Deployment
```powershell
# 1. Build new version
.\scripts\build-and-tag.ps1 -Version "v0.4.2"

# 2. Update docker-compose.prod.yml
# Change: image: leoklemet/applylens-api:v0.4.1
# To:     image: leoklemet/applylens-api:v0.4.2

# 3. Deploy
docker-compose -f docker-compose.prod.yml up -d --force-recreate api web

# 4. Verify
curl http://localhost:8003/healthz
curl http://localhost:5175/
```

### Hotfix Deployment
```powershell
# 1. Build and push immediately
.\scripts\build-and-tag.ps1 -Version "v0.4.2-hotfix" -Push

# 2. Update compose file
# (manual edit or sed/replace)

# 3. Deploy
docker-compose -f docker-compose.prod.yml up -d --force-recreate api web
```

### Emergency Rollback
```powershell
# Quick rollback to last known-good version
.\scripts\rollback.ps1 -Version "v0.4.1"

# Verify immediately
curl http://localhost:8003/healthz
docker logs applylens-api-prod --tail 50
```

## Version Numbering

Follow semantic versioning: `vMAJOR.MINOR.PATCH`

- **MAJOR**: Breaking API changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes and hotfixes

**Examples:**
- `v0.4.1` - Patch release (bug fix)
- `v0.5.0` - Minor release (new feature)
- `v1.0.0` - Major release (breaking change)
- `v0.4.2-hotfix` - Hotfix identifier

## Image Metadata

All built images include OCI labels:
- `org.opencontainers.image.revision` - Git commit SHA
- `org.opencontainers.image.created` - Build timestamp (ISO 8601)
- `org.opencontainers.image.source` - GitHub repository URL
- `org.opencontainers.image.title` - Service name
- `org.opencontainers.image.description` - Service description

**View metadata:**
```powershell
docker inspect leoklemet/applylens-api:v0.4.1 --format='{{json .Config.Labels}}' | ConvertFrom-Json
```

## Troubleshooting

### Build Fails
```powershell
# Clear build cache
docker builder prune -f

# Rebuild without cache
cd services/api  # or apps/web
docker build --no-cache -t leoklemet/applylens-api:v0.4.2 -f Dockerfile.prod .
```

### Rollback Fails
```powershell
# Check if target version exists
docker images | grep applylens-api

# Pull from registry if missing
docker pull leoklemet/applylens-api:v0.4.0

# Manual rollback
Copy-Item docker-compose.prod.yml.bak docker-compose.prod.yml
docker-compose -f docker-compose.prod.yml up -d --force-recreate api web
```

### Script Permission Error
```powershell
# Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or run with explicit bypass
pwsh -ExecutionPolicy Bypass -File .\scripts\build-and-tag.ps1 -Version "v0.4.2"
```

## Best Practices

1. **Always use dry-run first** when testing rollback
2. **Tag builds immediately** after successful testing
3. **Keep last 3-5 versions** locally for quick rollback
4. **Document changes** in DEPLOYMENT.md version history
5. **Test in staging** before production (when available)
6. **Monitor logs** for 5-10 minutes after deployment
7. **Backup compose file** before manual edits

## Registry Integration

### Push to Docker Hub
```powershell
# Login (once)
docker login

# Build and push
.\scripts\build-and-tag.ps1 -Version "v0.4.2" -Push

# Manual push
docker push leoklemet/applylens-api:v0.4.2
docker push leoklemet/applylens-web:v0.4.2
```

### Pull Specific Version
```powershell
docker pull leoklemet/applylens-api:v0.4.1
docker pull leoklemet/applylens-web:v0.4.1
```

## Support

For issues or questions:
1. Check `../docs/DEPLOYMENT.md` for full documentation
2. Review script output for error messages
3. Check Docker logs: `docker logs applylens-api-prod --tail 100`
4. Verify Docker Desktop is running
5. Check disk space: `docker system df`

## Contributing

When adding new deployment scripts:
1. Use PowerShell Core (cross-platform)
2. Include `-DryRun` flag for preview
3. Add color-coded output (success=green, warning=yellow, error=red)
4. Validate inputs before execution
5. Create backups before destructive operations
6. Update this README with usage examples
