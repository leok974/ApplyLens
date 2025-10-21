# Install JSON API Datasource Plugin for Grafana

## Method 1: Using grafana-cli (Recommended)

### Windows

If Grafana is installed as a standalone application or service:

```powershell
# Find Grafana installation directory
$grafanaPath = "C:\Program Files\GrafanaLabs\grafana"  # Adjust if different

# Navigate to Grafana bin directory
cd "$grafanaPath\bin"

# Install the plugin
.\grafana-cli.exe plugins install marcusolsson-json-datasource

# Restart Grafana service
Restart-Service grafana
```

Or if you know the Grafana CLI path:

```powershell
grafana-cli plugins install marcusolsson-json-datasource
```

### Alternative: Using Full Path

```powershell
# Common Grafana installation paths:
# C:\Program Files\GrafanaLabs\grafana\bin\grafana-cli.exe
# C:\Grafana\bin\grafana-cli.exe

& "C:\Program Files\GrafanaLabs\grafana\bin\grafana-cli.exe" plugins install marcusolsson-json-datasource
```

## Method 2: Docker Installation

If running Grafana in Docker:

```powershell
# Add plugin to docker-compose.yml or docker run command
# In docker-compose.yml, add:
environment:
  - GF_INSTALL_PLUGINS=marcusolsson-json-datasource

# Or rebuild with the plugin
docker exec -it grafana grafana-cli plugins install marcusolsson-json-datasource
docker restart grafana
```

## Method 3: Manual Installation

1. **Download the plugin:**
   - Visit: https://grafana.com/grafana/plugins/marcusolsson-json-datasource/
   - Click "Download"
   - Or download directly: https://github.com/marcusolsson/grafana-json-datasource/releases

2. **Extract to Grafana plugins directory:**

```powershell
# Find your Grafana plugins directory
# Common locations:
# - C:\Program Files\GrafanaLabs\grafana\data\plugins
# - C:\Grafana\data\plugins
# - %APPDATA%\grafana\plugins

# Extract the downloaded zip to the plugins directory
$pluginsDir = "C:\Program Files\GrafanaLabs\grafana\data\plugins"
# Extract marcusolsson-json-datasource to $pluginsDir
```

3. **Restart Grafana**

## Verify Installation

After installation and restart, verify the plugin:

```powershell
# Check if plugin is installed (requires API key)
curl.exe -H "Authorization: Bearer YOUR_API_KEY" http://localhost:3000/api/plugins | ConvertFrom-Json | Where-Object { $_.id -eq "marcusolsson-json-datasource" }
```

Or manually:
1. Open Grafana: http://localhost:3000
2. Go to: Configuration (⚙️) → Plugins
3. Search for: "JSON API"
4. Verify it shows as "Installed"

## Start Grafana (if not running)

### Windows Service

```powershell
# Check service status
Get-Service grafana -ErrorAction SilentlyContinue

# Start service
Start-Service grafana

# Or restart
Restart-Service grafana
```

### Standalone Application

If Grafana is installed as a standalone app, launch it from:
- Start Menu → Grafana
- Or run: `C:\Program Files\GrafanaLabs\grafana\bin\grafana-server.exe`

### Using Chocolatey (if installed via Chocolatey)

```powershell
# Reinstall/update Grafana with plugin support
choco upgrade grafana
```

## After Installation

Once the plugin is installed and Grafana is running:

1. **Create a datasource:**
   ```powershell
   # Go to: http://localhost:3000/datasources/new
   # Search: "JSON API"
   # Name: "ApplyLens API"
   # Click: Save & Test
   ```

2. **Import the dashboard:**
   ```powershell
   cd D:\ApplyLens\docs
   .\import_grafana_dashboard.ps1 -GrafanaUrl "http://localhost:3000" -ApiKey "YOUR_API_TOKEN"
   ```

## Troubleshooting

### Plugin Not Found After Installation

```powershell
# Check if plugin directory exists
$pluginPath = "C:\Program Files\GrafanaLabs\grafana\data\plugins\marcusolsson-json-datasource"
Test-Path $pluginPath

# If not found, check permissions
# Grafana service needs read access to plugins directory
```

### Grafana Service Won't Start

```powershell
# Check Grafana logs
Get-Content "C:\Program Files\GrafanaLabs\grafana\data\log\grafana.log" -Tail 50
```

### Permission Issues

Run PowerShell as Administrator when installing plugins.

## Quick Start Script

Save this as `install_grafana_plugin.ps1`:

```powershell
# Find Grafana installation
$possiblePaths = @(
    "C:\Program Files\GrafanaLabs\grafana",
    "C:\Grafana",
    "${env:ProgramFiles}\GrafanaLabs\grafana"
)

$grafanaPath = $possiblePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($grafanaPath) {
    Write-Host "Found Grafana at: $grafanaPath" -ForegroundColor Green
    
    $cliPath = Join-Path $grafanaPath "bin\grafana-cli.exe"
    
    if (Test-Path $cliPath) {
        Write-Host "Installing JSON API datasource plugin..." -ForegroundColor Cyan
        & $cliPath plugins install marcusolsson-json-datasource
        
        Write-Host "`nRestarting Grafana service..." -ForegroundColor Cyan
        Restart-Service grafana -ErrorAction SilentlyContinue
        
        Write-Host "`n✅ Plugin installed! Open Grafana and verify at Configuration → Plugins" -ForegroundColor Green
    } else {
        Write-Host "❌ grafana-cli.exe not found at: $cliPath" -ForegroundColor Red
    }
} else {
    Write-Host "❌ Grafana installation not found" -ForegroundColor Red
    Write-Host "Please install Grafana first or specify the correct path" -ForegroundColor Yellow
}
```

## Official Documentation

- Plugin Page: https://grafana.com/grafana/plugins/marcusolsson-json-datasource/
- GitHub: https://github.com/marcusolsson/grafana-json-datasource
- Grafana Plugin Installation: https://grafana.com/docs/grafana/latest/administration/plugin-management/
