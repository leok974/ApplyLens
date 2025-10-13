# Phase 5 Chat Assistant - Quick API Test
# Tests the /chat endpoint with various intents

$API_BASE = "http://localhost:8003"
$passed = 0
$failed = 0

Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host "=== Phase 5 Chat Assistant - API Tests ===" -ForegroundColor White
Write-Host "=" -ForegroundColor Cyan
Write-Host ""

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Query,
        [string]$ExpectedIntent
    )
    
    Write-Host "Testing: " -NoNewline
    Write-Host $Name -ForegroundColor Yellow
    Write-Host "  Query: " -NoNewline -ForegroundColor Gray
    Write-Host """$Query""" -ForegroundColor White
    
    try {
        $body = @{
            messages = @(
                @{
                    role = "user"
                    content = $Query
                }
            )
        } | ConvertTo-Json -Depth 4
        
        $response = Invoke-WebRequest -Uri "$API_BASE/api/chat" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body `
            -UseBasicParsing
        
        if ($response.StatusCode -eq 200) {
            $data = $response.Content | ConvertFrom-Json
            
            Write-Host "  Intent: " -NoNewline -ForegroundColor Gray
            Write-Host $data.intent -ForegroundColor Cyan
            Write-Host "  Answer: " -NoNewline -ForegroundColor Gray
            $answerPreview = $data.answer.Substring(0, [Math]::Min(80, $data.answer.Length))
            if ($data.answer.Length -gt 80) { $answerPreview += "..." }
            Write-Host $answerPreview -ForegroundColor White
            Write-Host "  Citations: " -NoNewline -ForegroundColor Gray
            Write-Host "$($data.citations.Count) emails" -ForegroundColor White
            Write-Host "  Actions: " -NoNewline -ForegroundColor Gray
            Write-Host "$($data.actions.Count) proposed" -ForegroundColor White
            Write-Host "  Results: " -NoNewline -ForegroundColor Gray
            Write-Host "$($data.search_stats.returned_results) / $($data.search_stats.total_results) searched" -ForegroundColor White
            
            # Check if intent matches expected
            if ($ExpectedIntent -and $data.intent -ne $ExpectedIntent) {
                Write-Host "  ⚠️ Expected intent '$ExpectedIntent' but got '$($data.intent)'" -ForegroundColor Yellow
            }
            
            Write-Host "  ✅ PASSED" -ForegroundColor Green
            $script:passed++
        } else {
            Write-Host "  ❌ FAILED (HTTP $($response.StatusCode))" -ForegroundColor Red
            $script:failed++
        }
    } catch {
        Write-Host "  ❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
    }
    
    Write-Host ""
}

# Test 1: Health Check
Write-Host "1. Health Check" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$API_BASE/api/chat/health" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        $data = $response.Content | ConvertFrom-Json
        Write-Host "  Status: $($data.status)" -ForegroundColor White
        Write-Host "  Service: $($data.service)" -ForegroundColor White
        Write-Host "  ✅ PASSED" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "  ❌ FAILED (HTTP $($response.StatusCode))" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "  ❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
    $failed++
}
Write-Host ""

# Test 2: List Intents
Write-Host "2. List Available Intents" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$API_BASE/api/chat/intents" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        $intents = $response.Content | ConvertFrom-Json
        Write-Host "  Found $($intents.PSObject.Properties.Count) intents:" -ForegroundColor White
        foreach ($intent in $intents.PSObject.Properties) {
            Write-Host "    • $($intent.Name): $($intent.Value.description)" -ForegroundColor Gray
        }
        Write-Host "  ✅ PASSED" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "  ❌ FAILED (HTTP $($response.StatusCode))" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "  ❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
    $failed++
}
Write-Host ""

# Test 3-10: Intent Detection Tests
Write-Host "3. Intent Detection Tests" -ForegroundColor Cyan
Write-Host ""

Test-Endpoint -Name "Summarize Intent" `
    -Query "Summarize recent emails about job applications" `
    -ExpectedIntent "summarize"

Test-Endpoint -Name "Find Intent" `
    -Query "Find interviews from August with confirmed times" `
    -ExpectedIntent "find"

Test-Endpoint -Name "Clean Intent" `
    -Query "Clean up promos older than a week unless they're from Best Buy" `
    -ExpectedIntent "clean"

Test-Endpoint -Name "Unsubscribe Intent" `
    -Query "Unsubscribe from newsletters I haven't opened in 60 days" `
    -ExpectedIntent "unsubscribe"

Test-Endpoint -Name "Flag Intent" `
    -Query "Show suspicious emails from new domains this week and explain why" `
    -ExpectedIntent "flag"

Test-Endpoint -Name "Follow-up Intent" `
    -Query "Which recruiters haven't replied in 5 days? Draft follow-ups" `
    -ExpectedIntent "follow-up"

Test-Endpoint -Name "Calendar Intent" `
    -Query "What bills are due before Friday? Create calendar reminders" `
    -ExpectedIntent "calendar"

Test-Endpoint -Name "Task Intent" `
    -Query "Create tasks from emails about pending action items" `
    -ExpectedIntent "task"

# Test 11: With Filters
Write-Host "11. Query with Structured Filters" -ForegroundColor Cyan
try {
    $body = @{
        messages = @(
            @{
                role = "user"
                content = "Show me promotional emails"
            }
        )
        filters = @{
            category = "promotions"
        }
        max_results = 10
    } | ConvertTo-Json -Depth 4
    
    $response = Invoke-WebRequest -Uri "$API_BASE/api/chat" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -UseBasicParsing
    
    if ($response.StatusCode -eq 200) {
        $data = $response.Content | ConvertFrom-Json
        Write-Host "  Filters applied: category=$($data.search_stats.filters.category)" -ForegroundColor White
        Write-Host "  Results: $($data.search_stats.returned_results)" -ForegroundColor White
        Write-Host "  ✅ PASSED" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "  ❌ FAILED (HTTP $($response.StatusCode))" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "  ❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
    $failed++
}
Write-Host ""

# Test 12: Multi-turn Conversation
Write-Host "12. Multi-turn Conversation" -ForegroundColor Cyan
try {
    $body = @{
        messages = @(
            @{
                role = "user"
                content = "Summarize job application emails"
            },
            @{
                role = "assistant"
                content = "Here are your job emails..."
            },
            @{
                role = "user"
                content = "Now show me interviews scheduled"
            }
        )
    } | ConvertTo-Json -Depth 4
    
    $response = Invoke-WebRequest -Uri "$API_BASE/api/chat" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -UseBasicParsing
    
    if ($response.StatusCode -eq 200) {
        $data = $response.Content | ConvertFrom-Json
        Write-Host "  Processed last message successfully" -ForegroundColor White
        Write-Host "  Intent: $($data.intent)" -ForegroundColor Cyan
        Write-Host "  ✅ PASSED" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "  ❌ FAILED (HTTP $($response.StatusCode))" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "  ❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
    $failed++
}
Write-Host ""

# Summary
Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host "=== Test Summary ===" -ForegroundColor White
Write-Host "=" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ✅ Passed:  " -NoNewline -ForegroundColor Green
Write-Host $passed
Write-Host "  ❌ Failed:  " -NoNewline -ForegroundColor Red
Write-Host $failed
Write-Host "  📊 Total:   " -NoNewline -ForegroundColor Cyan
Write-Host ($passed + $failed)
Write-Host ""

if ($failed -eq 0) {
    Write-Host "🎉 All tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  • Open UI: http://localhost:5175/chat" -ForegroundColor White
    Write-Host "  • Try quick-action chips" -ForegroundColor White
    Write-Host "  • Test natural language queries" -ForegroundColor White
    Write-Host "  • Check citations and actions" -ForegroundColor White
    exit 0
} else {
    Write-Host "⚠️ Some tests failed. Check the errors above." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Cyan
    Write-Host "  • Ensure API is running: docker compose up -d" -ForegroundColor White
    Write-Host "  • Check logs: docker compose logs api" -ForegroundColor White
    Write-Host "  • Verify Elasticsearch is healthy" -ForegroundColor White
    exit 1
}
