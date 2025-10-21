# Quick Test Script for Phase 4 AI Features

Write-Host "`n=== Phase 4 AI Features Test ===" -ForegroundColor Green
Write-Host "Testing all AI endpoints...`n" -ForegroundColor Cyan

# Test 1: AI Health
Write-Host "1. AI Health Check:" -ForegroundColor Yellow
try {
    $health = curl.exe -s http://127.0.0.1:8000/api/ai/health | ConvertFrom-Json
    if ($health.ollama -eq "available") {
        Write-Host "   ✓ PASS: Ollama is available" -ForegroundColor Green
        Write-Host "   Features: summarize=$($health.features.summarize)" -ForegroundColor Gray
    } else {
        Write-Host "   ✗ FAIL: Ollama unavailable" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ FAIL: Endpoint not responding" -ForegroundColor Red
}

# Test 2: Summarization Endpoint
Write-Host "`n2. Email Summarization:" -ForegroundColor Yellow
try {
    $response = curl.exe -s -X POST http://127.0.0.1:8000/api/ai/summarize `
        -H "Content-Type: application/json" `
        -d "@test_summarize.json"
    
    if ($response -like "*Thread not found*" -or $response -like "*summary*") {
        Write-Host "   ✓ PASS: Endpoint responding correctly" -ForegroundColor Green
        Write-Host "   Response: $response" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠ WARNING: Unexpected response" -ForegroundColor Yellow
        Write-Host "   Response: $response" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ✗ FAIL: Endpoint error" -ForegroundColor Red
}

# Test 3: RAG Health
Write-Host "`n3. RAG Search Health:" -ForegroundColor Yellow
try {
    $ragHealth = curl.exe -s http://127.0.0.1:8000/rag/health | ConvertFrom-Json
    Write-Host "   ✓ PASS: RAG endpoint responding" -ForegroundColor Green
    Write-Host "   Elasticsearch: $($ragHealth.elasticsearch_available)" -ForegroundColor Gray
    Write-Host "   Fallback mode: $($ragHealth.fallback_mode)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ FAIL: Endpoint not responding" -ForegroundColor Red
}

# Test 4: OpenAPI Routes
Write-Host "`n4. Phase 4 Routes Check:" -ForegroundColor Yellow
try {
    $openapi = curl.exe -s http://127.0.0.1:8000/openapi.json | ConvertFrom-Json
    $aiRoutes = @($openapi.paths.PSObject.Properties.Name | Where-Object { $_ -match "ai|rag|security.*risk" })
    
    if ($aiRoutes.Count -ge 3) {
        Write-Host "   ✓ PASS: Found $($aiRoutes.Count) Phase 4 routes" -ForegroundColor Green
        $aiRoutes | ForEach-Object { Write-Host "     - $_" -ForegroundColor Gray }
    } else {
        Write-Host "   ⚠ WARNING: Only found $($aiRoutes.Count) routes" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ✗ FAIL: Could not fetch routes" -ForegroundColor Red
}

# Summary
Write-Host "`n=== Test Complete ===" -ForegroundColor Green
Write-Host "`nFor full test with real email data:" -ForegroundColor Cyan
Write-Host "  1. Ensure PostgreSQL has email threads" -ForegroundColor White
Write-Host "  2. Replace 'test-thread' with real thread_id" -ForegroundColor White
Write-Host "  3. Re-run this script" -ForegroundColor White
Write-Host "`nDocumentation: PHASE_4_TEST_RESULTS.md`n" -ForegroundColor Gray
