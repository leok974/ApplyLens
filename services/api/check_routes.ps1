# Quick health & routes check for ApplyLens API

Write-Host "`n=== Checking API Server ===" -ForegroundColor Green

# Basic liveness
Write-Host "`n1. Basic Health Check:" -ForegroundColor Cyan
try {
    $health = curl.exe -s http://127.0.0.1:8000/health | ConvertFrom-Json
    Write-Host "   ✓ Server is responding" -ForegroundColor Green
    Write-Host "   Response: $($health | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ Server not responding" -ForegroundColor Red
    exit 1
}

# AI Health Check
Write-Host "`n2. AI Health Check:" -ForegroundColor Cyan
try {
    $aiHealth = curl.exe -s http://127.0.0.1:8000/api/ai/health | ConvertFrom-Json
    Write-Host "   ✓ AI endpoint responding" -ForegroundColor Green
    Write-Host "   Response: $($aiHealth | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ AI endpoint not found" -ForegroundColor Yellow
    Write-Host "   $_" -ForegroundColor Gray
}

# Check Phase 4 routes
Write-Host "`n3. Phase 4 Routes:" -ForegroundColor Cyan
try {
    $openapi = curl.exe -s http://127.0.0.1:8000/openapi.json | ConvertFrom-Json
    $phase4Routes = $openapi.paths.PSObject.Properties.Name | Where-Object { 
        $_ -match "(ai|rag|security)" 
    } | Sort-Object
    
    if ($phase4Routes) {
        Write-Host "   ✓ Found Phase 4 routes:" -ForegroundColor Green
        foreach ($route in $phase4Routes) {
            Write-Host "     - $route" -ForegroundColor Gray
        }
    } else {
        Write-Host "   ⚠ No Phase 4 routes found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ✗ Could not fetch routes" -ForegroundColor Red
}

# Check Ollama
Write-Host "`n4. Ollama Service:" -ForegroundColor Cyan
try {
    $ollama = curl.exe -s http://localhost:11434/api/tags | ConvertFrom-Json
    Write-Host "   ✓ Ollama is running" -ForegroundColor Green
    Write-Host "   Models: $($ollama.models.name -join ', ')" -ForegroundColor Gray
} catch {
    Write-Host "   ⚠ Ollama not responding" -ForegroundColor Yellow
}

Write-Host "`n=== All Checks Complete ===`n" -ForegroundColor Green
