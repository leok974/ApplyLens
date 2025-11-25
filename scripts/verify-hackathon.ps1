#!/usr/bin/env pwsh
# Verification script for hackathon setup
# Tests all components and provides health report

Write-Host "🔍 ApplyLens Hackathon Verification" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

# Test 1: Environment file
Write-Host "1. Checking environment configuration..." -ForegroundColor White
if (Test-Path "services/api/.env.hackathon") {
    Write-Host "   ✓ .env.hackathon exists" -ForegroundColor Green

    # Check for required variables
    $envContent = Get-Content "services/api/.env.hackathon" -Raw

    $requiredVars = @(
        "USE_GEMINI_FOR_CLASSIFY",
        "GOOGLE_CLOUD_PROJECT",
        "DD_SERVICE",
        "DD_API_KEY"
    )

    foreach ($var in $requiredVars) {
        if ($envContent -match "$var=") {
            Write-Host "   ✓ $var configured" -ForegroundColor Green
        } else {
            Write-Host "   ✗ $var missing" -ForegroundColor Red
            $allPassed = $false
        }
    }
} else {
    Write-Host "   ✗ .env.hackathon not found" -ForegroundColor Red
    $allPassed = $false
}

Write-Host ""

# Test 2: Docker services
Write-Host "2. Checking Docker services..." -ForegroundColor White
try {
    $services = docker ps --format "{{.Names}}" 2>$null

    $requiredServices = @(
        "applylens-api-hackathon",
        "applylens-datadog-agent",
        "applylens-db-hackathon",
        "applylens-redis-hackathon"
    )

    foreach ($service in $requiredServices) {
        if ($services -match $service) {
            Write-Host "   ✓ $service running" -ForegroundColor Green
        } else {
            Write-Host "   ✗ $service not running" -ForegroundColor Yellow
            Write-Host "     Run: docker-compose -f docker-compose.hackathon.yml up -d" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "   ✗ Cannot connect to Docker" -ForegroundColor Red
    $allPassed = $false
}

Write-Host ""

# Test 3: API health
Write-Host "3. Checking API health..." -ForegroundColor White
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health/live" -ErrorAction Stop -TimeoutSec 5

    if ($health.status -eq "ok") {
        Write-Host "   ✓ API is healthy" -ForegroundColor Green
    } else {
        Write-Host "   ✗ API unhealthy: $($health.status)" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host "   ✗ API not responding" -ForegroundColor Red
    Write-Host "     Check: docker logs applylens-api-hackathon" -ForegroundColor Gray
    $allPassed = $false
}

Write-Host ""

# Test 4: Gemini integration
Write-Host "4. Checking Gemini integration..." -ForegroundColor White
try {
    $llmStatus = Invoke-RestMethod -Uri "http://localhost:8000/debug/llm" -ErrorAction Stop -TimeoutSec 5

    Write-Host "   Provider: $($llmStatus.provider_active)" -ForegroundColor Gray

    if ($llmStatus.provider_active -eq "gemini") {
        Write-Host "   ✓ Gemini is active" -ForegroundColor Green
        Write-Host "     Model: $($llmStatus.gemini_model)" -ForegroundColor Gray
        Write-Host "     Project: $($llmStatus.google_cloud_project)" -ForegroundColor Gray
    } elseif ($llmStatus.provider_active -eq "heuristic_only") {
        Write-Host "   ⚠ Running in heuristic mode (Gemini not configured)" -ForegroundColor Yellow
        Write-Host "     This works but won't use Gemini API" -ForegroundColor Gray
    } else {
        Write-Host "   ✗ Unknown provider status" -ForegroundColor Red
        $allPassed = $false
    }

    # Test recent calls
    if ($llmStatus.stats_last_100.total_calls -gt 0) {
        Write-Host "   Recent calls: $($llmStatus.stats_last_100.total_calls)" -ForegroundColor Gray
        Write-Host "   Avg latency: $($llmStatus.stats_last_100.avg_latency_ms)ms" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ✗ Cannot check LLM status" -ForegroundColor Red
    $allPassed = $false
}

Write-Host ""

# Test 5: Test endpoints
Write-Host "5. Testing Gemini classification endpoint..." -ForegroundColor White
try {
    $testEmail = @{
        subject = "Interview invitation for Senior Engineer"
        snippet = "We'd like to schedule a technical interview"
        sender = "recruiter@techcorp.com"
    } | ConvertTo-Json

    $result = Invoke-RestMethod `
        -Uri "http://localhost:8000/hackathon/classify" `
        -Method POST `
        -Body $testEmail `
        -ContentType "application/json" `
        -ErrorAction Stop `
        -TimeoutSec 10

    Write-Host "   ✓ Classification endpoint works" -ForegroundColor Green
    Write-Host "     Intent: $($result.intent)" -ForegroundColor Gray
    Write-Host "     Confidence: $($result.confidence)" -ForegroundColor Gray
    Write-Host "     Model: $($result.model_used)" -ForegroundColor Gray
    Write-Host "     Latency: $($result.latency_ms)ms" -ForegroundColor Gray

    if ($result.intent -eq "interview") {
        Write-Host "   ✓ Correct classification" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ Unexpected classification" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ✗ Classification endpoint failed" -ForegroundColor Red
    Write-Host "     Error: $($_.Exception.Message)" -ForegroundColor Gray
    $allPassed = $false
}

Write-Host ""

# Test 6: Datadog agent
Write-Host "6. Checking Datadog agent..." -ForegroundColor White
try {
    $agentLogs = docker logs applylens-datadog-agent --tail 50 2>$null | Select-String "API key ending"

    if ($agentLogs) {
        Write-Host "   ✓ Datadog agent connected" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ Cannot verify Datadog connection" -ForegroundColor Yellow
        Write-Host "     Check: docker logs applylens-datadog-agent" -ForegroundColor Gray
    }

    # Check for errors
    $agentErrors = docker logs applylens-datadog-agent --tail 100 2>&1 | Select-String "ERROR"
    if ($agentErrors) {
        Write-Host "   ⚠ Found errors in agent logs:" -ForegroundColor Yellow
        $agentErrors | Select-Object -First 3 | ForEach-Object {
            Write-Host "     $($_.Line)" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "   ✗ Cannot check Datadog agent" -ForegroundColor Red
}

Write-Host ""

# Test 7: Python dependencies
Write-Host "7. Checking Python dependencies..." -ForegroundColor White
try {
    $pipList = docker exec applylens-api-hackathon pip list 2>$null

    $requiredPackages = @(
        "google-cloud-aiplatform",
        "ddtrace",
        "fastapi"
    )

    foreach ($package in $requiredPackages) {
        if ($pipList -match $package) {
            Write-Host "   ✓ $package installed" -ForegroundColor Green
        } else {
            Write-Host "   ✗ $package missing" -ForegroundColor Red
            Write-Host "     Run: docker exec applylens-api-hackathon pip install $package" -ForegroundColor Gray
            $allPassed = $false
        }
    }
} catch {
    Write-Host "   ⚠ Cannot check Python packages" -ForegroundColor Yellow
}

Write-Host ""

# Test 8: Traffic generator
Write-Host "8. Checking traffic generator..." -ForegroundColor White
if (Test-Path "scripts/traffic_generator.py") {
    Write-Host "   ✓ Traffic generator exists" -ForegroundColor Green

    # Check if httpx is installed
    try {
        python -c "import httpx" 2>$null
        Write-Host "   ✓ httpx dependency available" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠ httpx not installed (required for traffic generator)" -ForegroundColor Yellow
        Write-Host "     Run: pip install httpx" -ForegroundColor Gray
    }
} else {
    Write-Host "   ✗ Traffic generator not found" -ForegroundColor Red
    $allPassed = $false
}

Write-Host ""

# Summary
Write-Host "====================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "✅ All critical checks passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ready for demo! Next steps:" -ForegroundColor White
    Write-Host "1. Generate traffic: python scripts/traffic_generator.py --mode normal_traffic --rate 10 --duration 60" -ForegroundColor Gray
    Write-Host "2. Open Datadog dashboard to view metrics" -ForegroundColor Gray
    Write-Host "3. Trigger incident: python scripts/traffic_generator.py --mode latency_injection --rate 20 --duration 120" -ForegroundColor Gray
} else {
    Write-Host "⚠ Some checks failed" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Review errors above and fix before demo" -ForegroundColor White
    Write-Host "For help, see:" -ForegroundColor Gray
    Write-Host "- HACKATHON.md" -ForegroundColor Gray
    Write-Host "- hackathon/ARCHITECTURE.md" -ForegroundColor Gray
    Write-Host "- hackathon/TRAFFIC_GENERATOR.md" -ForegroundColor Gray
}
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
