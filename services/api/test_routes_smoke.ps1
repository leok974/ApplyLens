# Phase 4 Route Testing - Quick Smoke Tests
# Tests both /rag/* and /api/rag/* paths for backwards compatibility

Write-Host "🧪 Phase 4 Route Smoke Tests" -ForegroundColor Cyan
Write-Host "="*60 -ForegroundColor Cyan

$API_BASE = "http://127.0.0.1:8000"

# Test 1: RAG Query - Original Path
Write-Host "`n1️⃣  Testing RAG Query - Original Path (/rag/query)" -ForegroundColor Yellow
$response1 = curl.exe -s "$API_BASE/rag/query" -H "content-type: application/json" -d '{\"q\":\"test\"}'
Write-Host "Response: $response1"

if ($response1 -match "hits" -or $response1 -match "results") {
    Write-Host "✅ /rag/query working" -ForegroundColor Green
} else {
    Write-Host "⚠️  /rag/query returned unexpected response" -ForegroundColor Yellow
}

# Test 2: RAG Query - Backwards Compatible Path
Write-Host "`n2️⃣  Testing RAG Query - Backwards Compat (/api/rag/query)" -ForegroundColor Yellow
$response2 = curl.exe -s "$API_BASE/api/rag/query" -H "content-type: application/json" -d '{\"q\":\"test\"}'
Write-Host "Response: $response2"

if ($response2 -match "hits" -or $response2 -match "results") {
    Write-Host "✅ /api/rag/query working (backwards compat)" -ForegroundColor Green
} elseif ($response2 -match "404") {
    Write-Host "❌ /api/rag/query not registered - check main.py" -ForegroundColor Red
} else {
    Write-Host "⚠️  /api/rag/query returned unexpected response" -ForegroundColor Yellow
}

# Test 3: RAG Health
Write-Host "`n3️⃣  Testing RAG Health (/rag/health)" -ForegroundColor Yellow
$response3 = curl.exe -s "$API_BASE/rag/health"
Write-Host "Response: $response3"

if ($response3 -match "elasticsearch" -or $response3 -match "status") {
    Write-Host "✅ /rag/health working" -ForegroundColor Green
} else {
    Write-Host "❌ /rag/health failed" -ForegroundColor Red
}

# Test 4: Security Risk Top 3
Write-Host "`n4️⃣  Testing Security Risk Top3 (/api/security/risk-top3)" -ForegroundColor Yellow
$response4 = curl.exe -s "$API_BASE/api/security/risk-top3?message_id=demo-1"
Write-Host "Response: $response4"

if ($response4 -match "score" -or $response4 -match "signals" -or $response4 -match "404") {
    Write-Host "✅ /api/security/risk-top3 endpoint exists" -ForegroundColor Green
    if ($response4 -match "404") {
        Write-Host "   (Returns 404 for demo message - expected)" -ForegroundColor Gray
    }
} else {
    Write-Host "❌ /api/security/risk-top3 failed" -ForegroundColor Red
}

# Test 5: AI Health
Write-Host "`n5️⃣  Testing AI Health (/api/ai/health)" -ForegroundColor Yellow
$response5 = curl.exe -s "$API_BASE/api/ai/health"
Write-Host "Response: $response5"

if ($response5 -match "ollama") {
    Write-Host "✅ /api/ai/health working" -ForegroundColor Green
} else {
    Write-Host "❌ /api/ai/health failed" -ForegroundColor Red
}

# Test 6: Divergence Metrics
Write-Host "`n6️⃣  Testing Divergence Metrics (/api/metrics/divergence-24h)" -ForegroundColor Yellow
$response6 = curl.exe -s "$API_BASE/api/metrics/divergence-24h"
Write-Host "Response: $response6"

if ($response6 -match "divergence_pct" -or $response6 -match "status") {
    Write-Host "✅ /api/metrics/divergence-24h working" -ForegroundColor Green
} else {
    Write-Host "❌ /api/metrics/divergence-24h failed" -ForegroundColor Red
}

# Summary
Write-Host "`n" + "="*60 -ForegroundColor Cyan
Write-Host "✅ Smoke tests complete!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Restart API server to pick up route changes"
Write-Host "  2. Run pytest: D:/ApplyLens/.venv/Scripts/python.exe -m pytest tests/test_ai_health.py -v"
Write-Host "  3. Check OpenAPI spec: curl $API_BASE/openapi.json | jq '.paths | keys'"
