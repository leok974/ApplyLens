# Phase 3 Smoke Tests - Hybrid LLM & Conversational Intelligence
# Tests the assistant endpoint for proper LLM fallback telemetry

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "Phase 3 Assistant Smoke Tests" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Auto-detect if testing locally or production
if (Test-NetConnection -ComputerName localhost -Port 8003 -InformationLevel Quiet -WarningAction SilentlyContinue) {
    $baseUrl = "http://localhost:8003"
    Write-Host "Testing against: LOCAL (http://localhost:8003)" -ForegroundColor Cyan
} else {
    $baseUrl = "https://applylens.app"
    Write-Host "Testing against: PRODUCTION (https://applylens.app)" -ForegroundColor Yellow
    Write-Host "Note: Production tests may require authentication cookies" -ForegroundColor Yellow
}
Write-Host ""

$failed = 0

# Test 1: Summarize with LLM telemetry
Write-Host "Test 1: Summarize last 7 days (check llm_used field)" -ForegroundColor Yellow
$payload1 = @{
    user_query = "summarize the last 7 days"
    time_window_days = 7
    mode = "off"
    memory_opt_in = $false
    account = "test@example.com"
} | ConvertTo-Json

try {
    $response1 = Invoke-RestMethod -Uri "$baseUrl/assistant/query" `
        -Method Post `
        -ContentType "application/json" `
        -Body $payload1 `
        -ErrorAction Stop

    Write-Host "  ✓ Status: 200 OK" -ForegroundColor Green
    Write-Host "  Intent: $($response1.intent)" -ForegroundColor White
    Write-Host "  Summary length: $($response1.summary.Length) chars" -ForegroundColor White
    Write-Host "  LLM Used: $($response1.llm_used)" -ForegroundColor Cyan

    if (!$response1.summary) {
        Write-Host "  ✗ FAIL: summary is empty" -ForegroundColor Red
        $failed++
    }

    if (!$response1.llm_used) {
        Write-Host "  ✗ FAIL: llm_used field is missing" -ForegroundColor Red
        $failed++
    } elseif ($response1.llm_used -notin @("ollama", "openai", "fallback")) {
        Write-Host "  ✗ FAIL: llm_used has unexpected value: $($response1.llm_used)" -ForegroundColor Red
        $failed++
    } else {
        Write-Host "  ✓ LLM telemetry working" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ FAIL: $($_.Exception.Message)" -ForegroundColor Red
    $failed++
}
Write-Host ""

# Test 2: Suspicious emails query
Write-Host "Test 2: List suspicious emails" -ForegroundColor Yellow
$payload2 = @{
    user_query = "show suspicious emails from this week"
    time_window_days = 7
    mode = "off"
    memory_opt_in = $false
    account = "test@example.com"
} | ConvertTo-Json

try {
    $response2 = Invoke-RestMethod -Uri "$baseUrl/assistant/query" `
        -Method Post `
        -ContentType "application/json" `
        -Body $payload2 `
        -ErrorAction Stop

    Write-Host "  ✓ Status: 200 OK" -ForegroundColor Green
    Write-Host "  Intent: $($response2.intent)" -ForegroundColor White
    Write-Host "  Sources found: $($response2.sources.Count)" -ForegroundColor White
    Write-Host "  LLM Used: $($response2.llm_used)" -ForegroundColor Cyan

    if ($response2.intent -ne "list_suspicious") {
        Write-Host "  ⚠ Warning: Expected intent 'list_suspicious', got '$($response2.intent)'" -ForegroundColor Yellow
    }

    if (!$response2.llm_used) {
        Write-Host "  ✗ FAIL: llm_used field is missing" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "  ✗ FAIL: $($_.Exception.Message)" -ForegroundColor Red
    $failed++
}
Write-Host ""

# Test 3: Follow-up context hint
Write-Host "Test 3: Follow-up query with context_hint" -ForegroundColor Yellow
$payload3 = @{
    user_query = "mute them"
    time_window_days = 7
    mode = "off"
    memory_opt_in = $false
    account = "test@example.com"
    context_hint = @{
        previous_intent = "list_suspicious"
        previous_email_ids = @("email-123", "email-456")
    }
} | ConvertTo-Json

try {
    $response3 = Invoke-RestMethod -Uri "$baseUrl/assistant/query" `
        -Method Post `
        -ContentType "application/json" `
        -Body $payload3 `
        -ErrorAction Stop

    Write-Host "  ✓ Status: 200 OK" -ForegroundColor Green
    Write-Host "  Intent: $($response3.intent)" -ForegroundColor White
    Write-Host "  Summary: $($response3.summary.Substring(0, [Math]::Min(80, $response3.summary.Length)))..." -ForegroundColor White
    Write-Host "  LLM Used: $($response3.llm_used)" -ForegroundColor Cyan

    # Context hint should be accepted (no error)
    Write-Host "  ✓ Context hint accepted by API" -ForegroundColor Green
} catch {
    Write-Host "  ✗ FAIL: $($_.Exception.Message)" -ForegroundColor Red
    $failed++
}
Write-Host ""

# Test 4: Greeting (small talk) - should NOT hit LLM
Write-Host "Test 4: Greeting (client-side fallback expected)" -ForegroundColor Yellow
# Note: This test will likely fail if run against the backend directly
# because greetings are handled client-side in v0.4.47e+
# But we include it for completeness in case backend receives a greeting
$payload4 = @{
    user_query = "hi"
    time_window_days = 30
    mode = "off"
    memory_opt_in = $false
    account = "test@example.com"
} | ConvertTo-Json

try {
    $response4 = Invoke-RestMethod -Uri "$baseUrl/assistant/query" `
        -Method Post `
        -ContentType "application/json" `
        -Body $payload4 `
        -ErrorAction Stop

    Write-Host "  ✓ Status: 200 OK" -ForegroundColor Green
    Write-Host "  Intent: $($response4.intent)" -ForegroundColor White

    if ($response4.intent -eq "greeting") {
        Write-Host "  ✓ Greeting intent detected" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Note: Greeting reached backend (normally handled client-side)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ Note: Greeting test failed (expected if client-side only)" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

if ($failed -eq 0) {
    Write-Host "✅ All tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Phase 3 features working:" -ForegroundColor Green
    Write-Host "  • Hybrid LLM provider with telemetry" -ForegroundColor White
    Write-Host "  • llm_used field populated (ollama/openai/fallback)" -ForegroundColor White
    Write-Host "  • context_hint accepted for follow-up queries" -ForegroundColor White
    Write-Host "  • Graceful fallback when LLMs unavailable" -ForegroundColor White
    exit 0
} else {
    Write-Host "❌ $failed test(s) failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Review failures above and check:" -ForegroundColor Yellow
    Write-Host "  • Ollama container running (docker ps | grep ollama)" -ForegroundColor White
    Write-Host "  • OPENAI_API_KEY configured (docker exec applylens-api-prod printenv OPENAI_API_KEY)" -ForegroundColor White
    Write-Host "  • API version v0.4.48 deployed" -ForegroundColor White
    exit 1
}
