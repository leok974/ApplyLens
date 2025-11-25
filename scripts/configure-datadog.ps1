# Configure ApplyLens API to Use Datadog Agent
# This script sets up the Datadog integration for the hackathon

param(
    [string]$ApiContainer = "applylens-api-prod",
    [string]$DatadogAgent = "dd-agent",
    [switch]$Test
)

Write-Host "🔧 Configuring Datadog Integration..." -ForegroundColor Cyan

# 1. Ensure Datadog agent is on the same network
Write-Host "`n1️⃣ Connecting Datadog agent to ApplyLens network..." -ForegroundColor Yellow
try {
    docker network connect applylens_applylens-prod $DatadogAgent 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Datadog agent connected to network" -ForegroundColor Green
    } else {
        Write-Host "   ℹ️ Datadog agent already on network" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ⚠️ Network connection skipped" -ForegroundColor Gray
}

# 2. Test connection from API to Datadog
Write-Host "`n2️⃣ Testing connection from API to Datadog..." -ForegroundColor Yellow
$testResult = docker exec $ApiContainer sh -c "nc -zv dd-agent 8125 2>&1" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ API can reach Datadog StatsD (port 8125)" -ForegroundColor Green
} else {
    Write-Host "   ⚠️ Testing network connectivity..." -ForegroundColor Yellow
    docker exec $ApiContainer sh -c "ping -c 1 dd-agent" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Network connection OK" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Cannot reach dd-agent from API container" -ForegroundColor Red
    }
}

# 3. Send test metric
Write-Host "`n3️⃣ Sending test metric to Datadog..." -ForegroundColor Yellow
$pythonTest = @"
from datadog import initialize, statsd
import os

# Initialize with Datadog agent
initialize(
    statsd_host='dd-agent',
    statsd_port=8125,
    statsd_namespace='applylens'
)

# Send test metrics
statsd.increment('hackathon.test.connection', tags=['env:hackathon', 'test:true'])
statsd.gauge('hackathon.test.value', 42, tags=['env:hackathon', 'test:true'])
statsd.histogram('hackathon.test.latency', 123, tags=['env:hackathon', 'test:true'])

print('✅ Test metrics sent successfully!')
print('   - applylens.hackathon.test.connection (counter)')
print('   - applylens.hackathon.test.value (gauge)')
print('   - applylens.hackathon.test.latency (histogram)')
"@

docker exec $ApiContainer python -c $pythonTest
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Test metrics sent to Datadog" -ForegroundColor Green
} else {
    Write-Host "   ❌ Failed to send test metrics" -ForegroundColor Red
}

# 4. Verify metrics in Datadog agent
Write-Host "`n4️⃣ Verifying metrics received by Datadog agent..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
$agentStats = docker exec $DatadogAgent agent status 2>&1 | Select-String -Pattern "Dogstatsd Metric Sample|Metric Packets"
Write-Host "   $agentStats" -ForegroundColor Gray

# 5. Display configuration summary
Write-Host "`n📊 Configuration Summary:" -ForegroundColor Cyan
Write-Host "   Container:      $ApiContainer" -ForegroundColor White
Write-Host "   Datadog Agent:  $DatadogAgent" -ForegroundColor White
Write-Host "   StatsD Host:    dd-agent" -ForegroundColor White
Write-Host "   StatsD Port:    8125" -ForegroundColor White
Write-Host "   APM Port:       8126" -ForegroundColor White
Write-Host "   Environment:    hackathon" -ForegroundColor White

Write-Host "`n📝 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Check metrics in Datadog UI: https://us5.datadoghq.com/metric/explorer" -ForegroundColor White
Write-Host "   2. Search for: applylens.hackathon.test.*" -ForegroundColor White
Write-Host "   3. Run traffic generator: python scripts/traffic_generator.py" -ForegroundColor White
Write-Host "   4. Create dashboard following: hackathon/DATADOG_SETUP.md" -ForegroundColor White

Write-Host "`n✅ Configuration complete!`n" -ForegroundColor Green
