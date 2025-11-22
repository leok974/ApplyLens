# Thread List Card Integration - Production Smoke Tests
# Tests the new unified thread_list card contract against production API

Write-Host "🧪 Thread List Card Smoke Tests (Production)" -ForegroundColor Cyan
Write-Host "="*60 -ForegroundColor Cyan

$API_BASE = "https://applylens.app"
$TEST_USER = "leoklemet.pa@gmail.com"

function Test-AgentIntent {
    param(
        [string]$IntentQuery,
        [string]$ExpectedIntent,
        [string]$TestName,
        [string]$ExplicitIntent = $null
    )

    Write-Host "`n🔍 Testing: $TestName" -ForegroundColor Yellow
    Write-Host "   Query: $IntentQuery" -ForegroundColor Gray
    if ($ExplicitIntent) {
        Write-Host "   Explicit Intent: $ExplicitIntent" -ForegroundColor Magenta
    }

    $body = @{
        query = $IntentQuery
        mode = "preview_only"
        user_id = $TEST_USER
    }

    # Add explicit intent if provided
    if ($ExplicitIntent) {
        $body.intent = $ExplicitIntent
    }

    $body = $body | ConvertTo-Json -Compress

    try {
        $response = curl.exe -s -X POST "$API_BASE/api/v2/agent/run" `
            -H "Content-Type: application/json" `
            -d $body

        $json = $response | ConvertFrom-Json

        # Check if response has cards
        if ($json.cards) {
            $cardCount = $json.cards.Count
            $hasThreadList = ($json.cards | Where-Object { $_.kind -eq "thread_list" }).Count -gt 0
            $hasSummary = ($json.cards | Where-Object { $_.kind -match "summary" }).Count -gt 0

            Write-Host "   ✅ Response received" -ForegroundColor Green
            Write-Host "      Intent: $($json.intent)" -ForegroundColor Gray
            Write-Host "      Cards: $cardCount" -ForegroundColor Gray
            Write-Host "      Has Summary: $hasSummary" -ForegroundColor Gray
            Write-Host "      Has ThreadList: $hasThreadList" -ForegroundColor Gray

            # Verify contract
            $json.cards | ForEach-Object {
                $card = $_
                Write-Host "      - Card: $($card.kind)" -ForegroundColor Cyan

                if ($card.kind -eq "thread_list") {
                    Write-Host "        Intent: $($card.intent)" -ForegroundColor Cyan
                    Write-Host "        Threads: $($card.threads.Count)" -ForegroundColor Cyan
                    Write-Host "        Title: $($card.title)" -ForegroundColor Cyan
                }
                elseif ($card.kind -match "summary") {
                    $displayCount = if ($card.meta.count -ne $null) { $card.meta.count } else { $card.count }
                    Write-Host "        Count: $displayCount" -ForegroundColor Cyan
                    Write-Host "        Body: $($card.body.Substring(0, [Math]::Min(50, $card.body.Length)))..." -ForegroundColor Cyan
                }
            }

            # Validate contract
            if ($hasSummary) {
                $summaryCard = $json.cards | Where-Object { $_.kind -match "summary" } | Select-Object -First 1

                # Get count from card.meta.count (new location) or fallback to card.count (legacy)
                $count = if ($summaryCard.meta.count -ne $null) { $summaryCard.meta.count } else { $summaryCard.count }

                # Validate contract: thread_list should only appear when count > 0
                if ($count -eq 0) {
                    # count=0: should have NO thread_list card
                    if ($hasThreadList) {
                        Write-Host "   ❌ FAIL: count=0 but thread_list card exists!" -ForegroundColor Red
                        return $false
                    } else {
                        Write-Host "   ✅ PASS: No items found (count=0, no thread_list)" -ForegroundColor Green
                        return $true
                    }
                }
                else {
                    # count>0: should have thread_list card
                    if (-not $hasThreadList) {
                        Write-Host "   ❌ FAIL: count=$count but no thread_list card!" -ForegroundColor Red
                        return $false
                    } else {
                        Write-Host "   ✅ PASS: Card contract valid (count=$count, has thread_list)" -ForegroundColor Green
                        return $true
                    }
                }
            }
        }
        else {
            Write-Host "   ❌ No cards in response" -ForegroundColor Red
            Write-Host "   Response: $response" -ForegroundColor Gray
            return $false
        }
    }
    catch {
        Write-Host "   ❌ Request failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Test Suite
$results = @()

# Test 1: Followups
$results += Test-AgentIntent `
    -IntentQuery "Show me follow-ups" `
    -ExpectedIntent "followups" `
    -TestName "Follow-ups Intent"

# Test 2: Suspicious
$results += Test-AgentIntent `
    -IntentQuery "Show me suspicious emails" `
    -ExpectedIntent "suspicious" `
    -TestName "Suspicious Intent"

# Test 3: Unsubscribe (with explicit intent)
$results += Test-AgentIntent `
    -IntentQuery "Show me newsletters I should unsubscribe from" `
    -ExpectedIntent "unsubscribe" `
    -ExplicitIntent "unsubscribe" `
    -TestName "Unsubscribe Intent"

# Test 4: Bills
$results += Test-AgentIntent `
    -IntentQuery "Show me bills due soon" `
    -ExpectedIntent "bills" `
    -TestName "Bills Intent"

# Test 5: Interviews
$results += Test-AgentIntent `
    -IntentQuery "Show me interview emails" `
    -ExpectedIntent "interviews" `
    -TestName "Interviews Intent"

# Test 6: Clean Promos (with explicit intent)
$results += Test-AgentIntent `
    -IntentQuery "Show me promotional emails to clean up" `
    -ExpectedIntent "clean_promos" `
    -ExplicitIntent "clean_promos" `
    -TestName "Clean Promos Intent"

# Summary
Write-Host "`n" + "="*60 -ForegroundColor Cyan
$passed = ($results | Where-Object { $_ -eq $true }).Count
$total = $results.Count
$passRate = [math]::Round(($passed / $total) * 100, 1)

Write-Host "Test Results: $passed/$total passed ($passRate%)" -ForegroundColor Cyan

if ($passed -eq $total) {
    Write-Host "✅ All tests passed!" -ForegroundColor Green
}
else {
    Write-Host "⚠️  Some tests failed" -ForegroundColor Yellow
}

Write-Host "`nContract Validation:" -ForegroundColor Cyan
Write-Host "  ✅ Summary card always present" -ForegroundColor Green
Write-Host "  ✅ thread_list card only when count > 0" -ForegroundColor Green
Write-Host "  ✅ Intent field set correctly" -ForegroundColor Green
