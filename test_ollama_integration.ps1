# Test Ollama Integration with Phase 4 AI Features
# Run this script to verify gpt-oss:20b model works with ApplyLens

Write-Host "=== Testing Ollama Integration with gpt-oss:20b ===" -ForegroundColor Cyan

# 1. Check Ollama service
Write-Host "`n[1/5] Checking Ollama service..." -ForegroundColor Yellow
try {
    $version = Invoke-RestMethod -Uri 'http://localhost:11434/api/version' -Method Get
    Write-Host "✓ Ollama is running (version: $($version.version))" -ForegroundColor Green
} catch {
    Write-Host "✗ Ollama service not running!" -ForegroundColor Red
    Write-Host "  Run: ollama serve" -ForegroundColor Yellow
    exit 1
}

# 2. Check gpt-oss:20b model
Write-Host "`n[2/5] Checking gpt-oss:20b model..." -ForegroundColor Yellow
$models = ollama list | Select-String "gpt-oss:20b"
if ($models) {
    Write-Host "✓ Model gpt-oss:20b is available" -ForegroundColor Green
} else {
    Write-Host "✗ Model gpt-oss:20b not found!" -ForegroundColor Red
    Write-Host "  Run: ollama pull gpt-oss:20b" -ForegroundColor Yellow
    exit 1
}

# 3. Test direct Ollama chat
Write-Host "`n[3/5] Testing direct Ollama chat..." -ForegroundColor Yellow
$body = @{
    model = 'gpt-oss:20b'
    messages = @(
        @{
            role = 'user'
            content = 'Respond with just: OLLAMA_OK'
        }
    )
    stream = $false
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri 'http://localhost:11434/api/chat' -Method Post -Body $body -ContentType 'application/json'
    if ($response.message.content -match 'OLLAMA_OK') {
        Write-Host "✓ Direct Ollama chat works" -ForegroundColor Green
        Write-Host "  Response time: $([math]::Round($response.total_duration / 1000000000, 2))s" -ForegroundColor Gray
    } else {
        Write-Host "✓ Ollama responded: $($response.message.content)" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Ollama chat failed: $_" -ForegroundColor Red
    exit 1
}

# 4. Check if API server is running
Write-Host "`n[4/5] Checking API server..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri 'http://localhost:8000/health' -Method Get -ErrorAction Stop
    Write-Host "✓ API server is running" -ForegroundColor Green
} catch {
    Write-Host "✗ API server not running!" -ForegroundColor Red
    Write-Host "  Start it with: cd services/api && uvicorn app.main:app --reload" -ForegroundColor Yellow
    Write-Host "`n  Before starting, set environment variables:" -ForegroundColor Yellow
    Write-Host "  `$env:OLLAMA_BASE='http://localhost:11434'" -ForegroundColor Gray
    Write-Host "  `$env:OLLAMA_MODEL='gpt-oss:20b'" -ForegroundColor Gray
    Write-Host "  `$env:FEATURE_SUMMARIZE='true'" -ForegroundColor Gray
    Write-Host "  `$env:FEATURE_RAG_SEARCH='true'" -ForegroundColor Gray
    exit 1
}

# 5. Test AI health endpoint
Write-Host "`n[5/5] Testing AI health endpoint..." -ForegroundColor Yellow
try {
    $aiHealth = Invoke-RestMethod -Uri 'http://localhost:8000/api/ai/health' -Method Get
    Write-Host "✓ AI health endpoint works" -ForegroundColor Green
    Write-Host "  Feature enabled: $($aiHealth.feature_enabled)" -ForegroundColor Gray
    Write-Host "  Ollama available: $($aiHealth.ollama_available)" -ForegroundColor Gray
    Write-Host "  Model: $($aiHealth.ollama_model)" -ForegroundColor Gray
} catch {
    Write-Host "⚠ AI endpoint not accessible (this is OK if routers not registered yet)" -ForegroundColor Yellow
    Write-Host "  Error: $_" -ForegroundColor Gray
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Set environment variables (if not already set):" -ForegroundColor White
Write-Host "   `$env:OLLAMA_BASE='http://localhost:11434'" -ForegroundColor Gray
Write-Host "   `$env:OLLAMA_MODEL='gpt-oss:20b'" -ForegroundColor Gray
Write-Host "`n2. Test the summarizer endpoint:" -ForegroundColor White
Write-Host "   `$body = @{thread_id='demo-1'; max_citations=3} | ConvertTo-Json" -ForegroundColor Gray
Write-Host "   Invoke-RestMethod -Uri 'http://localhost:8000/api/ai/summarize' -Method Post -Body `$body -ContentType 'application/json'" -ForegroundColor Gray
Write-Host "`n3. See PHASE_4_DEMO_SCRIPTS.md for more examples" -ForegroundColor White
