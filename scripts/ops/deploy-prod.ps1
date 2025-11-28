# deploy-prod.ps1 - PowerShell deployment script for ApplyLens on Windows
# Usage: .\deploy-prod.ps1

$ErrorActionPreference = "Stop"

# Configuration
$ComposeFile = "docker-compose.prod.yml"
$EnvFile = "infra\.env"
$SecretsDir = "infra\secrets"

# Colors
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Status($message) {
    Write-ColorOutput Cyan "[*] $message"
}

function Write-Success($message) {
    Write-ColorOutput Green "[✓] $message"
}

function Write-Error($message) {
    Write-ColorOutput Red "[✗] $message"
}

function Write-Warning($message) {
    Write-ColorOutput Yellow "[!] $message"
}

# Header
Write-Host ""
Write-ColorOutput Cyan "╔════════════════════════════════════════════════════════════╗"
Write-ColorOutput Cyan "║         ApplyLens Production Stack Deployment             ║"
Write-ColorOutput Cyan "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

# Check prerequisites
Write-Status "Checking prerequisites..."

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed. Please install Docker Desktop first."
    exit 1
}

if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
}

Write-Success "Docker and Docker Compose found"

# Check if .env file exists
if (-not (Test-Path $EnvFile)) {
    Write-Warning ".env file not found. Creating from template..."
    if (Test-Path "infra\.env.example") {
        Copy-Item "infra\.env.example" $EnvFile
        Write-Success "Created $EnvFile from template"
        Write-Warning "Please edit $EnvFile with your production values before continuing!"
        Read-Host "Press Enter when ready to continue"
    } else {
        Write-Error "Template file infra\.env.example not found!"
        exit 1
    }
}

# Check for required secrets
Write-Status "Checking for required secrets..."
if (-not (Test-Path $SecretsDir)) {
    New-Item -ItemType Directory -Path $SecretsDir -Force | Out-Null
    Write-Success "Created secrets directory"
}

if (-not (Test-Path "$SecretsDir\google.json")) {
    Write-Warning "Google OAuth credentials not found at $SecretsDir\google.json"
    Write-Warning "Gmail integration will not work without this file."
    Write-Warning "Download from Google Cloud Console and save to $SecretsDir\google.json"
}

# Ask for deployment mode
Write-Host ""
Write-Status "Select deployment mode:"
Write-Host "  1) Fresh deployment (stop existing, remove volumes, start fresh)"
Write-Host "  2) Update deployment (rebuild and restart services, keep data)"
Write-Host "  3) Quick restart (restart services only, no rebuild)"
Write-Host ""
$choice = Read-Host "Enter choice [1-3]"

$FreshDeploy = $false

switch ($choice) {
    "1" {
        Write-Warning "This will DELETE ALL EXISTING DATA!"
        $confirm = Read-Host "Are you sure? (yes/no)"
        if ($confirm -ne "yes") {
            Write-Error "Deployment cancelled"
            exit 0
        }

        Write-Status "Stopping existing services..."
        docker-compose -f $ComposeFile down -v 2>$null
        Write-Success "Stopped and removed volumes"

        Write-Status "Building images..."
        docker-compose -f $ComposeFile build --no-cache
        Write-Success "Built images"

        Write-Status "Starting services..."
        docker-compose -f $ComposeFile up -d
        Write-Success "Services started"

        $FreshDeploy = $true
    }
    "2" {
        Write-Status "Stopping services..."
        docker-compose -f $ComposeFile down
        Write-Success "Stopped services"

        Write-Status "Rebuilding images..."
        docker-compose -f $ComposeFile build
        Write-Success "Rebuilt images"

        Write-Status "Starting services..."
        docker-compose -f $ComposeFile up -d
        Write-Success "Services started"
    }
    "3" {
        Write-Status "Restarting services..."
        docker-compose -f $ComposeFile restart
        Write-Success "Services restarted"
    }
    default {
        Write-Error "Invalid choice"
        exit 1
    }
}

# Wait for services to be ready
Write-Host ""
Write-Status "Waiting for services to be ready..."
Start-Sleep -Seconds 5

# Check service health
Write-Status "Checking service health..."
$Healthy = $true

function Test-ServiceHealth($serviceName, $url) {
    $maxAttempts = 30
    $attempt = 0

    while ($attempt -lt $maxAttempts) {
        try {
            $response = Invoke-WebRequest -Uri $url -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Success "$serviceName is healthy"
                return $true
            }
        } catch {
            # Service not ready yet
        }
        $attempt++
        Start-Sleep -Seconds 2
    }

    Write-Error "$serviceName failed to become healthy"
    return $false
}

$Healthy = $Healthy -and (Test-ServiceHealth "Elasticsearch" "http://localhost:9200/_cluster/health")
$Healthy = $Healthy -and (Test-ServiceHealth "API" "http://localhost:8003/healthz")
$Healthy = $Healthy -and (Test-ServiceHealth "Frontend" "http://localhost:5175/")
$Healthy = $Healthy -and (Test-ServiceHealth "Kibana" "http://localhost:5601/api/status")
$Healthy = $Healthy -and (Test-ServiceHealth "Prometheus" "http://localhost:9090/-/healthy")
$Healthy = $Healthy -and (Test-ServiceHealth "Grafana" "http://localhost:3000/api/health")

# Run migrations if fresh deployment
if ($FreshDeploy) {
    Write-Host ""
    Write-Status "Running database migrations..."
    try {
        docker-compose -f $ComposeFile exec -T api alembic upgrade head
        Write-Success "Migrations completed"
    } catch {
        Write-Error "Migration failed"
        $Healthy = $false
    }
}

# Display status
Write-Host ""
Write-ColorOutput Cyan "╔════════════════════════════════════════════════════════════╗"
Write-ColorOutput Cyan "║                   Deployment Summary                       ║"
Write-ColorOutput Cyan "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

if ($Healthy) {
    Write-Success "All services are healthy!"
} else {
    Write-Warning "Some services may have issues. Check logs with:"
    Write-Host "  docker-compose -f $ComposeFile logs -f"
}

Write-Host ""
Write-Status "Service URLs:"
Write-Host "  🌐 Frontend:      http://localhost:5175"
Write-Host "  🔧 API:           http://localhost:8003"
Write-Host "  📊 API Docs:      http://localhost:8003/docs"
Write-Host "  🔍 Elasticsearch: http://localhost:9200"
Write-Host "  📈 Kibana:        http://localhost:5601"
Write-Host "  📉 Prometheus:    http://localhost:9090"
Write-Host "  📊 Grafana:       http://localhost:3000"
Write-Host "  🔀 Nginx:         http://localhost:80"

Write-Host ""
Write-Status "Useful commands:"
Write-Host "  📋 View logs:     docker-compose -f $ComposeFile logs -f"
Write-Host "  🔄 Restart:       docker-compose -f $ComposeFile restart"
Write-Host "  ⏹️  Stop:          docker-compose -f $ComposeFile down"
Write-Host "  💾 Backup DB:     docker-compose -f $ComposeFile exec db pg_dump -U postgres applylens > backup.sql"

Write-Host ""
Write-Status "Documentation:"
Write-Host "  📖 Deployment guide: PRODUCTION_DEPLOYMENT.md"
Write-Host "  🎤 Demo guide:       README.md (Judge Demo section)"

Write-Host ""
if ($Healthy) {
    Write-ColorOutput Green "╔════════════════════════════════════════════════════════════╗"
    Write-ColorOutput Green "║            ✓ Deployment completed successfully!           ║"
    Write-ColorOutput Green "╚════════════════════════════════════════════════════════════╝"
} else {
    Write-ColorOutput Yellow "╔════════════════════════════════════════════════════════════╗"
    Write-ColorOutput Yellow "║        ⚠ Deployment completed with warnings               ║"
    Write-ColorOutput Yellow "╚════════════════════════════════════════════════════════════╝"
}

Write-Host ""
