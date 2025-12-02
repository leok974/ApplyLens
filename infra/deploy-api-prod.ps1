# Deploy ApplyLens API to Production
# Usage: .\deploy-api-prod.ps1 [image-tag]
#
# REQUIRED ENVIRONMENT VARIABLES:
#   - APPLYLENS_DB_PASSWORD (or use infra/.env.prod)
#   - APPLYLENS_SESSION_SECRET (or use infra/.env.prod)
#   - GOOGLE_CLIENT_ID (or use infra/.env.prod)
#   - GOOGLE_CLIENT_SECRET (or use infra/.env.prod)

param(
    [string]$ImageTag = "latest"
)

# Load environment from infra/.env.prod if it exists
$envFile = "$PSScriptRoot/../infra/.env.prod"
if (Test-Path $envFile) {
    Write-Host "📄 Loading environment from infra/.env.prod" -ForegroundColor Cyan
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+?)\s*=\s*(.+?)\s*$') {
            $name = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$ContainerName = "applylens-api-prod"
$ImageName = "leoklemet/applylens-api:$ImageTag"

# Get credentials from environment
$DbPassword = $env:POSTGRES_PASSWORD
$SessionSecret = $env:APPLYLENS_SESSION_SECRET
$GoogleClientId = $env:GOOGLE_CLIENT_ID
$GoogleClientSecret = $env:GOOGLE_CLIENT_SECRET

if (-not $DbPassword) {
    Write-Error "❌ POSTGRES_PASSWORD not set. Set in environment or infra/.env.prod"
    exit 1
}

Write-Host "🚀 Deploying ApplyLens API: $ImageName" -ForegroundColor Cyan

# Stop and remove existing container
Write-Host "📦 Stopping existing container..." -ForegroundColor Yellow
docker rm -f $ContainerName 2>$null

# Start new container
Write-Host "🔧 Starting new container..." -ForegroundColor Yellow
docker run -d `
  --name $ContainerName `
  --network applylens_applylens-prod `
  -p 8003:8003 `
  --restart unless-stopped `
  -e DATABASE_URL="postgresql://postgres:${DbPassword}@applylens-db-prod:5432/applylens" `
  -e ELASTICSEARCH_URL="http://applylens-es-prod:9200" `
  -e REDIS_URL="redis://applylens-redis-prod:6379/0" `
  -e APPLYLENS_SESSION_SECRET="$SessionSecret" `
  -e APPLYLENS_GOOGLE_CLIENT_ID="$GoogleClientId" `
  -e APPLYLENS_GOOGLE_CLIENT_SECRET="$GoogleClientSecret" `
  -e APPLYLENS_OAUTH_REDIRECT_URI="https://applylens.app/auth/google/callback" `
  -e APPLYLENS_COOKIE_DOMAIN="applylens.app" `
  -e APPLYLENS_COOKIE_SECURE="1" `
  -e SKIP_DOTENV="1" `
  -e CREATE_TABLES_ON_STARTUP="0" `
  $ImageName

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container started successfully" -ForegroundColor Green
    Write-Host "📊 Checking status..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    docker ps --filter "name=$ContainerName" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
} else {
    Write-Host "❌ Failed to start container" -ForegroundColor Red
    exit 1
}
