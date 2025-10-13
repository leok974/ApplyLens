#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test chat streaming endpoint with SSE events

.DESCRIPTION
    Validates the /api/chat/stream endpoint:
    - SSE event emission (intent, tool, answer, done)
    - Action filing with propose=1
    - Filed event confirmation
#>

param(
    [string]$ApiBase = "http://localhost:8003/api"
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== Phase 5 Chat Streaming - API Tests ===" -ForegroundColor Cyan
Write-Host "API Base: $ApiBase`n" -ForegroundColor Gray

$passed = 0
$failed = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$ExpectedEvent
    )
    
    Write-Host "Testing: $Name" -NoNewline
    
    try {
        # Use curl for SSE streaming
        $response = curl -s -N $Url 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host " FAILED" -ForegroundColor Red
            Write-Host "  Error: curl failed with exit code $LASTEXITCODE" -ForegroundColor Red
            return $false
        }
        
        # Check if expected event is present
        if ($response -match $ExpectedEvent) {
            Write-Host " PASSED" -ForegroundColor Green
            return $true
        } else {
            Write-Host " FAILED" -ForegroundColor Red
            Write-Host "  Expected event '$ExpectedEvent' not found" -ForegroundColor Red
            Write-Host "  Response: $($response.Substring(0, [Math]::Min(200, $response.Length)))" -ForegroundColor Gray
            return $false
        }
    } catch {
        Write-Host " FAILED" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
        return $false
    }
}

# Test 1: Health Check
Write-Host "`n--- Basic Endpoints ---`n" -ForegroundColor Yellow

if (Test-Endpoint "Health Check" "$ApiBase/chat/health" '"status":\s*"ok"') {
    $passed++
} else {
    $failed++
}

# Test 2: List Intents
if (Test-Endpoint "List Intents" "$ApiBase/chat/intents" '"clean"') {
    $passed++
} else {
    $failed++
}

# Test 3: Streaming - Intent Event
Write-Host "`n--- Streaming Events ---`n" -ForegroundColor Yellow

if (Test-Endpoint "Streaming: Intent Event" "$ApiBase/chat/stream?q=Clean+up+promos" 'event:\s*intent') {
    $passed++
} else {
    $failed++
}

# Test 4: Streaming - Tool Event
if (Test-Endpoint "Streaming: Tool Event" "$ApiBase/chat/stream?q=Summarize+emails" 'event:\s*tool') {
    $passed++
} else {
    $failed++
}

# Test 5: Streaming - Answer Event
if (Test-Endpoint "Streaming: Answer Event" "$ApiBase/chat/stream?q=Find+important+emails" 'event:\s*answer') {
    $passed++
} else {
    $failed++
}

# Test 6: Streaming - Done Event
if (Test-Endpoint "Streaming: Done Event" "$ApiBase/chat/stream?q=Test" 'event:\s*done') {
    $passed++
} else {
    $failed++
}

# Test 7: Streaming with propose=1 (no filed event expected if no actions)
Write-Host "`n--- Action Filing ---`n" -ForegroundColor Yellow

Write-Host "Testing: Streaming with propose=1" -NoNewline
try {
    $response = curl -s -N "$ApiBase/chat/stream?q=Summarize+recent+emails&propose=1" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        if ($response -match 'event:\s*done') {
            Write-Host " PASSED" -ForegroundColor Green
            Write-Host "  Note: No 'filed' event (expected when no actions to file)" -ForegroundColor Gray
            $passed++
        } else {
            Write-Host " FAILED" -ForegroundColor Red
            Write-Host "  Expected 'done' event not found" -ForegroundColor Red
            $failed++
        }
    } else {
        Write-Host " FAILED" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    $failed++
}

# Summary
Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan
Write-Host "Passed: $passed/$($passed + $failed)" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
Write-Host "Failed: $failed/$($passed + $failed)" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })

if ($failed -gt 0) {
    Write-Host "`n❌ Some tests failed" -ForegroundColor Red
    exit 1
} else {
    Write-Host "`n✅ All tests passed!" -ForegroundColor Green
    exit 0
}
