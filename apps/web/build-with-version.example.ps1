# Example build script showing how to inject version into the web app
# This would typically be run in CI/CD or local builds

# Generate version string from git
$GIT_SHA = (git rev-parse --short HEAD).Trim()
$GIT_BRANCH = (git rev-parse --abbrev-ref HEAD).Trim()
$BUILD_DATE = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$APP_VERSION = "v0.6.0-${GIT_BRANCH}+${GIT_SHA}"

Write-Host "Building ApplyLens Web with version: ${APP_VERSION}" -ForegroundColor Green

# Build Docker image with version injected
docker build `
  -t leoklemet/applylens-web:latest `
  -t leoklemet/applylens-web:${GIT_BRANCH} `
  --build-arg APP_VERSION="${APP_VERSION}" `
  --build-arg GIT_SHA="${GIT_SHA}" `
  --build-arg BUILD_DATE="${BUILD_DATE}" `
  -f Dockerfile.prod `
  .

Write-Host "Build complete!" -ForegroundColor Green
Write-Host "Version: ${APP_VERSION}"
Write-Host "`nCheck version with:"
Write-Host "  docker run --rm leoklemet/applylens-web:latest cat /usr/share/nginx/html/version.json" -ForegroundColor Cyan
