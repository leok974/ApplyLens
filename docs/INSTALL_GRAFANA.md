# Install Grafana on Windows - Quick Guide

## Prerequisites

You need to install Grafana before you can add plugins and import dashboards.

## Method 1: Using Chocolatey (Recommended - Easiest)

If you have Chocolatey installed:

```powershell
# Run PowerShell as Administrator
choco install grafana

# Start Grafana service
Start-Service grafana

# Check status
Get-Service grafana
```

### Install Chocolatey First (if needed)

```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

## Method 2: Standalone Installer (Most Common)

### Download and Install

1. **Download Grafana:**
   - Go to: https://grafana.com/grafana/download?platform=windows
   - Choose: "Standalone Windows Binaries" (ZIP file)
   - Or MSI installer for service installation

2. **Install using MSI (Recommended):**
   - Download: `grafana-enterprise-{version}.windows-amd64.msi`
   - Double-click to install
   - Default location: `C:\Program Files\GrafanaLabs\grafana`
   - Installs as Windows service (auto-starts)

3. **Or extract ZIP (Portable):**
   ```powershell
   # Download ZIP file
   # Extract to C:\Grafana (or any location)
   
   # Start Grafana manually
   cd C:\Grafana\bin
   .\grafana-server.exe
   ```

### Verify Installation

```powershell
# Check service (if installed as MSI)
Get-Service grafana

# Or check if accessible
curl.exe http://localhost:3000/api/health
```

## Method 3: Docker (Alternative)

If you prefer Docker:

```powershell
# Pull Grafana image
docker pull grafana/grafana:latest

# Run Grafana with plugin pre-installed
docker run -d `
  --name=grafana `
  -p 3000:3000 `
  -e "GF_INSTALL_PLUGINS=marcusolsson-json-datasource" `
  grafana/grafana:latest

# Check status
docker ps | Select-String grafana
```

### Or use Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_INSTALL_PLUGINS=marcusolsson-json-datasource
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
    volumes:
      - grafana-storage:/var/lib/grafana

volumes:
  grafana-storage:
```

Then run:

```powershell
docker-compose up -d
```

## Post-Installation Steps

### 1. Access Grafana

Open browser: http://localhost:3000

**Default credentials:**
- Username: `admin`
- Password: `admin`
- (You'll be prompted to change password on first login)

### 2. Install JSON API Plugin

**After Grafana is running**, install the plugin:

```powershell
cd D:\ApplyLens\docs
.\install_grafana_plugin.ps1
```

### 3. Create Datasource

1. Go to: Configuration (⚙️) → Data Sources
2. Click: "Add data source"
3. Search: "JSON API"
4. Configure:
   - **Name:** `ApplyLens API`
   - **URL:** Leave empty (panels use their own URLs)
5. Click: "Save & Test"

### 4. Import Dashboard

```powershell
cd D:\ApplyLens\docs

# Verify setup
.\verify_grafana_setup.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_KEY"

# Import dashboard
.\import_grafana_dashboard.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_KEY"
```

## Quick Start Script

Save as `setup_grafana_windows.ps1`:

```powershell
# Complete Grafana setup for ApplyLens
# Run as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Grafana Setup for ApplyLens" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Chocolatey is available
$chocoInstalled = $null -ne (Get-Command choco -ErrorAction SilentlyContinue)

if ($chocoInstalled) {
    Write-Host "✅ Chocolatey found" -ForegroundColor Green
    Write-Host ""
    
    $response = Read-Host "Install Grafana via Chocolatey? (Y/n)"
    if ($response -ne "n" -and $response -ne "N") {
        Write-Host "Installing Grafana..." -ForegroundColor Cyan
        choco install grafana -y
        
        Write-Host "Starting Grafana service..." -ForegroundColor Cyan
        Start-Service grafana
        
        Start-Sleep -Seconds 5
        
        Write-Host "✅ Grafana installed and running!" -ForegroundColor Green
        Write-Host ""
    }
} else {
    Write-Host "❌ Chocolatey not found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please install Grafana manually:" -ForegroundColor Yellow
    Write-Host "  1. Download: https://grafana.com/grafana/download?platform=windows" -ForegroundColor Gray
    Write-Host "  2. Install MSI or extract ZIP" -ForegroundColor Gray
    Write-Host "  3. Start Grafana service or run grafana-server.exe" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

# Install plugin
Write-Host "Installing JSON API plugin..." -ForegroundColor Cyan
cd D:\ApplyLens\docs
.\install_grafana_plugin.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Open: http://localhost:3000" -ForegroundColor White
Write-Host "  2. Login: admin / admin (change password)" -ForegroundColor White
Write-Host "  3. Create datasource: 'ApplyLens API' (JSON API type)" -ForegroundColor White
Write-Host "  4. Import dashboard: .\import_grafana_dashboard.ps1" -ForegroundColor White
Write-Host ""
```

## Verification Checklist

After installation, verify:

- [ ] Grafana accessible at http://localhost:3000
- [ ] Can login with admin credentials
- [ ] Grafana service running (for MSI install)
- [ ] Plugin installation script runs without errors
- [ ] JSON API plugin visible in Configuration → Plugins

## Troubleshooting

### Port 3000 Already in Use

```powershell
# Find what's using port 3000
netstat -ano | findstr :3000

# Stop the process (replace PID with actual process ID)
Stop-Process -Id <PID> -Force
```

### Service Won't Start

```powershell
# Check service status
Get-Service grafana | Format-List

# Check logs
Get-Content "C:\Program Files\GrafanaLabs\grafana\data\log\grafana.log" -Tail 50
```

### Permission Issues

- Run PowerShell as Administrator
- Check file permissions in Grafana directory
- Ensure user has write access to data folder

## Alternative: Use Docker

If you prefer not to install Grafana natively:

```powershell
# Quick Docker setup with plugin
docker run -d `
  --name=grafana `
  -p 3000:3000 `
  -e "GF_INSTALL_PLUGINS=marcusolsson-json-datasource" `
  -e "GF_AUTH_ANONYMOUS_ENABLED=true" `
  -e "GF_AUTH_ANONYMOUS_ORG_ROLE=Admin" `
  grafana/grafana:latest

# Wait for startup
Start-Sleep -Seconds 10

# Verify
curl.exe http://localhost:3000/api/health
```

## Official Resources

- **Grafana Downloads:** https://grafana.com/grafana/download
- **Windows Installation Docs:** https://grafana.com/docs/grafana/latest/setup-grafana/installation/windows/
- **Docker Installation:** https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/
- **Plugin Documentation:** https://grafana.com/docs/grafana/latest/administration/plugin-management/

## Summary

**Recommended approach for Windows:**

1. Install Grafana MSI from official site
2. Verify service is running
3. Run `install_grafana_plugin.ps1` script
4. Create datasource in Grafana UI
5. Import dashboard with `import_grafana_dashboard.ps1`

**For Docker users:**

Use the docker-compose.yml with pre-installed plugin, then import dashboard directly.
