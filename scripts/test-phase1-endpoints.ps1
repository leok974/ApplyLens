#!/usr/bin/env pwsh
# Test script for Phase-1 gap closure implementation

Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Phase-1 Gap Closure - API Endpoint Tests                   ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$baseUrl = "http://localhost:8000"
$passed = 0
$failed = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [hashtable]$Body = $null
    )
    
    Write-Host "🧪 Testing: $Name" -ForegroundColor Yellow
    Write-Host "   URL: $Url" -ForegroundColor Gray
    
    try {
        if ($Method -eq "GET") {
            $response = Invoke-RestMethod -Uri $Url -Method GET -ErrorAction Stop
        } else {
            $jsonBody = $Body | ConvertTo-Json
            $response = Invoke-RestMethod -Uri $Url -Method POST -Body $jsonBody -ContentType "application/json" -ErrorAction Stop
        }
        
        Write-Host "   ✅ PASSED" -ForegroundColor Green
        $script:passed++
        return $response
    } catch {
        Write-Host "   ❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
        return $null
    }
}

# Test 1: Health check
Write-Host "`n📍 Basic Health Checks" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Test-Endpoint "Health Check" "$baseUrl/health"

# Test 2: Search endpoint
Write-Host "`n📍 Search Endpoint Tests" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
$searchResult = Test-Endpoint "Search (q=interview)" "$baseUrl/search/?q=interview&size=5"

if ($searchResult -and $searchResult.hits.Count -gt 0) {
    Write-Host "   📊 Found $($searchResult.total) results" -ForegroundColor Cyan
    $testDocId = $searchResult.hits[0].gmail_id
    if (-not $testDocId) {
        $testDocId = $searchResult.hits[0].id
    }
    Write-Host "   📄 Using doc ID for tests: $testDocId" -ForegroundColor Cyan
    
    # Test 3: Explain endpoint
    Write-Host "`n📍 Explain Endpoint Test" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    $explainResult = Test-Endpoint "Explain Email" "$baseUrl/search/explain/$testDocId"
    
    if ($explainResult) {
        Write-Host "   📝 Reason: $($explainResult.reason)" -ForegroundColor Cyan
        Write-Host "   🔍 Evidence:" -ForegroundColor Cyan
        if ($explainResult.evidence.labels) {
            Write-Host "      • Labels: $($explainResult.evidence.labels -join ', ')" -ForegroundColor Gray
        }
        if ($explainResult.evidence.sender_domain) {
            Write-Host "      • Domain: $($explainResult.evidence.sender_domain)" -ForegroundColor Gray
        }
    }
    
    # Test 4: Quick Actions (dry-run)
    Write-Host "`n📍 Quick Actions Tests (Dry-Run)" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    
    $actionBody = @{
        doc_id = $testDocId
        note = "Test from automated script"
    }
    
    Test-Endpoint "Archive Action" "$baseUrl/search/actions/archive" "POST" $actionBody
    Test-Endpoint "Mark Safe Action" "$baseUrl/search/actions/mark_safe" "POST" $actionBody
    Test-Endpoint "Mark Suspicious Action" "$baseUrl/search/actions/mark_suspicious" "POST" $actionBody
    Test-Endpoint "Unsubscribe (Dry-Run)" "$baseUrl/search/actions/unsubscribe_dryrun" "POST" $actionBody
    
    # Test 5: Verify audit log
    Write-Host "`n📍 Audit Log Verification" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    try {
        $auditResult = Invoke-RestMethod -Uri "http://localhost:9200/applylens_audit/_search?size=5&sort=timestamp:desc" -Method GET
        if ($auditResult.hits.total.value -gt 0) {
            Write-Host "   ✅ Audit log has $($auditResult.hits.total.value) entries" -ForegroundColor Green
            Write-Host "   📝 Latest actions:" -ForegroundColor Cyan
            foreach ($hit in $auditResult.hits.hits) {
                $action = $hit._source.action
                $docId = $hit._source.doc_id
                $timestamp = $hit._source.timestamp
                Write-Host "      • $action on $docId at $timestamp" -ForegroundColor Gray
            }
            $script:passed++
        } else {
            Write-Host "   ⚠️  Audit log is empty (actions may not have been recorded)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "   ❌ Failed to query audit log: $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
    }
} else {
    Write-Host "   ⚠️  No search results found - skipping explain and action tests" -ForegroundColor Yellow
    Write-Host "   💡 Make sure you have emails indexed in Elasticsearch" -ForegroundColor Cyan
}

# Summary
Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Test Results Summary                                        ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Host "   ✅ Passed: $passed" -ForegroundColor Green
Write-Host "   ❌ Failed: $failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
Write-Host ""

if ($failed -eq 0) {
    Write-Host "🎉 All tests passed! Phase-1 implementation is working." -ForegroundColor Green
    exit 0
} else {
    Write-Host "⚠️  Some tests failed. Check the output above for details." -ForegroundColor Yellow
    exit 1
}
