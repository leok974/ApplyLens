# Automated Grafana JSON API Plugin Installation Script
# Run as Administrator for best results

param(
    [Parameter(Mandatory=$false)]
    [string]$GrafanaPath = "",

    [Parameter(Mandatory=$false)]
    [switch]$SkipRestart
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Grafana JSON API Plugin Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  Warning: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "   Some operations may fail without admin privileges" -ForegroundColor Yellow
    Write-Host ""
}

# Find Grafana installation
Write-Host "1️⃣  Locating Grafana installation..." -ForegroundColor White

if ($GrafanaPath -and (Test-Path $GrafanaPath)) {
    Write-Host "   Using provided path: $GrafanaPath" -ForegroundColor Gray
} else {
    $possiblePaths = @(
        "C:\Program Files\GrafanaLabs\grafana",
        "C:\Program Files\Grafana",
        "C:\Grafana",
        "${env:ProgramFiles}\GrafanaLabs\grafana",
        "${env:ProgramFiles(x86)}\GrafanaLabs\grafana",
        "$env:LOCALAPPDATA\Grafana"
    )

    Write-Host "   Searching common locations..." -ForegroundColor Gray
    $GrafanaPath = $possiblePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $GrafanaPath) {
    Write-Host ""
    Write-Host "❌ Error: Grafana installation not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Grafana first:" -ForegroundColor Yellow
    Write-Host "  • Download: https://grafana.com/grafana/download" -ForegroundColor Gray
    Write-Host "  • Or use Chocolatey: choco install grafana" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Or specify the path manually:" -ForegroundColor Yellow
    Write-Host "  .\install_grafana_plugin.ps1 -GrafanaPath 'C:\path\to\grafana'" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host "   ✅ Found Grafana at: $GrafanaPath" -ForegroundColor Green
Write-Host ""

# Check for grafana-cli
Write-Host "2️⃣  Checking grafana-cli..." -ForegroundColor White

$cliPath = Join-Path $GrafanaPath "bin\grafana-cli.exe"

if (-not (Test-Path $cliPath)) {
    Write-Host "   ❌ grafana-cli.exe not found at: $cliPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Your Grafana installation may be incomplete." -ForegroundColor Yellow
    Write-Host "   Expected structure:" -ForegroundColor Yellow
    Write-Host "     $GrafanaPath\" -ForegroundColor Gray
    Write-Host "       ├── bin\" -ForegroundColor Gray
    Write-Host "       │   ├── grafana-server.exe" -ForegroundColor Gray
    Write-Host "       │   └── grafana-cli.exe" -ForegroundColor Gray
    Write-Host "       └── data\plugins\" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host "   ✅ Found grafana-cli: $cliPath" -ForegroundColor Green
Write-Host ""

# Check if plugin already installed
Write-Host "3️⃣  Checking existing installation..." -ForegroundColor White

$pluginsDir = Join-Path $GrafanaPath "data\plugins"
$pluginPath = Join-Path $pluginsDir "marcusolsson-json-datasource"

if (Test-Path $pluginPath) {
    Write-Host "   ⚠️  Plugin already installed at: $pluginPath" -ForegroundColor Yellow
    Write-Host ""

    $response = Read-Host "   Reinstall? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host ""
        Write-Host "   Skipping installation" -ForegroundColor Gray
        Write-Host ""
        Write-Host "✅ Plugin is already available" -ForegroundColor Green
        Write-Host ""
        exit 0
    }

    Write-Host ""
    Write-Host "   Removing existing installation..." -ForegroundColor Yellow
    Remove-Item $pluginPath -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "   Plugin not installed yet" -ForegroundColor Gray
Write-Host ""

# Install plugin
Write-Host "4️⃣  Installing JSON API datasource plugin..." -ForegroundColor White
Write-Host ""

try {
    # Run grafana-cli
    $installOutput = & $cliPath plugins install marcusolsson-json-datasource 2>&1

    Write-Host "   Installation output:" -ForegroundColor Gray
    $installOutput | ForEach-Object { Write-Host "     $_" -ForegroundColor DarkGray }
    Write-Host ""

    # Verify installation
    if (Test-Path $pluginPath) {
        Write-Host "   ✅ Plugin installed successfully!" -ForegroundColor Green
        Write-Host "      Location: $pluginPath" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠️  Installation completed but plugin directory not found" -ForegroundColor Yellow
        Write-Host "      Expected at: $pluginPath" -ForegroundColor Gray
    }

} catch {
    Write-Host "   ❌ Installation failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Try manually:" -ForegroundColor Yellow
    Write-Host "     & '$cliPath' plugins install marcusolsson-json-datasource" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host ""

# Restart Grafana service
if (-not $SkipRestart) {
    Write-Host "5️⃣  Restarting Grafana service..." -ForegroundColor White

    try {
        $service = Get-Service -Name "grafana" -ErrorAction SilentlyContinue

        if ($service) {
            Write-Host "   Found Grafana service: $($service.Status)" -ForegroundColor Gray

            if ($service.Status -eq "Running") {
                Write-Host "   Stopping Grafana..." -ForegroundColor Gray
                Stop-Service grafana -ErrorAction Stop
                Start-Sleep -Seconds 2
            }

            Write-Host "   Starting Grafana..." -ForegroundColor Gray
            Start-Service grafana -ErrorAction Stop

            # Wait for service to start
            Start-Sleep -Seconds 3

            $service = Get-Service -Name "grafana"
            if ($service.Status -eq "Running") {
                Write-Host "   ✅ Grafana service restarted successfully" -ForegroundColor Green
            } else {
                Write-Host "   ⚠️  Grafana service status: $($service.Status)" -ForegroundColor Yellow
            }

        } else {
            Write-Host "   ⚠️  Grafana service not found" -ForegroundColor Yellow
            Write-Host "      If running Grafana manually, please restart it now" -ForegroundColor Yellow
            Write-Host "      Start: & '$GrafanaPath\bin\grafana-server.exe'" -ForegroundColor Gray
        }

    } catch {
        Write-Host "   ⚠️  Could not restart service: $_" -ForegroundColor Yellow
        Write-Host "      Please restart Grafana manually" -ForegroundColor Yellow
    }

    Write-Host ""
} else {
    Write-Host "5️⃣  Skipping Grafana restart (use -SkipRestart to avoid this)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   ⚠️  Remember to restart Grafana for the plugin to load!" -ForegroundColor Yellow
    Write-Host "      Restart-Service grafana" -ForegroundColor Gray
    Write-Host ""
}

# Verify Grafana is accessible
Write-Host "6️⃣  Verifying Grafana accessibility..." -ForegroundColor White

Start-Sleep -Seconds 2

try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing -TimeoutSec 5
    $health = $response.Content | ConvertFrom-Json

    Write-Host "   ✅ Grafana is accessible!" -ForegroundColor Green
    Write-Host "      URL: http://localhost:3000" -ForegroundColor Gray
    Write-Host "      Version: $($health.version)" -ForegroundColor Gray
    Write-Host ""

} catch {
    Write-Host "   ⚠️  Grafana not accessible at http://localhost:3000" -ForegroundColor Yellow
    Write-Host "      It may still be starting up..." -ForegroundColor Yellow
    Write-Host ""
}

# Final instructions
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host ""

Write-Host "1️⃣  Verify plugin in Grafana UI:" -ForegroundColor White
Write-Host "   • Open: http://localhost:3000" -ForegroundColor Gray
Write-Host "   • Go to: Configuration (⚙️) → Plugins" -ForegroundColor Gray
Write-Host "   • Search: 'JSON API'" -ForegroundColor Gray
Write-Host "   • Status should show: ✅ Installed" -ForegroundColor Gray
Write-Host ""

Write-Host "2️⃣  Create datasource:" -ForegroundColor White
Write-Host "   • Go to: Configuration → Data Sources → Add data source" -ForegroundColor Gray
Write-Host "   • Search: 'JSON API'" -ForegroundColor Gray
Write-Host "   • Name: 'ApplyLens API'" -ForegroundColor Gray
Write-Host "   • No URL needed (uses panel-specific URLs)" -ForegroundColor Gray
Write-Host "   • Click: Save & Test" -ForegroundColor Gray
Write-Host ""

Write-Host "3️⃣  Import dashboard:" -ForegroundColor White
Write-Host "   cd D:\ApplyLens\docs" -ForegroundColor Gray
Write-Host "   .\import_grafana_dashboard.ps1 -GrafanaUrl 'http://localhost:3000' -ApiKey 'YOUR_API_TOKEN'" -ForegroundColor Gray
Write-Host ""

Write-Host "Or verify setup first:" -ForegroundColor White
Write-Host "   .\verify_grafana_setup.ps1 -GrafanaUrl 'http://localhost:3000' -ApiKey 'YOUR_API_TOKEN'" -ForegroundColor Gray
Write-Host ""

Write-Host "📚 Documentation: INSTALL_GRAFANA_PLUGIN.md" -ForegroundColor Cyan
Write-Host ""
