# Verify Style Preferences Endpoint
# Tests that the API accepts style_prefs without 422 errors

Write-Host "`n🧪 Testing Style Preferences Endpoint..." -ForegroundColor Cyan

$testCases = @(
    @{
        name = "Friendly + Short"
        tone = "friendly"
        length = "short"
    },
    @{
        name = "Confident + Medium"
        tone = "confident"
        length = "medium"
    },
    @{
        name = "Detailed + Long"
        tone = "detailed"
        length = "long"
    }
)

foreach ($test in $testCases) {
    Write-Host "`nTesting: $($test.name)" -ForegroundColor Yellow

    $payload = @{
        job = @{
            title = "Test Engineer"
            company = "Test Co"
            url = "https://example.com/job"
        }
        fields = @(
            @{
                field_id = "why_interested"
                semantic_key = "why_interested"
                label = "Why are you interested?"
                type = "textarea"
            }
        )
        style_prefs = @{
            tone = $test.tone
            length = $test.length
        }
    } | ConvertTo-Json -Depth 10

    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8003/api/extension/generate-form-answers" `
            -Method POST `
            -Headers @{"Content-Type" = "application/json"} `
            -Body $payload

        $answer = ($response.answers | Where-Object { $_.field_id -eq "why_interested" }).answer
        Write-Host "  ✅ Status: OK" -ForegroundColor Green
        Write-Host "  📏 Length: $($answer.Length) chars" -ForegroundColor Gray
        Write-Host "  📝 Answer: $($answer.Substring(0, [Math]::Min(100, $answer.Length)))..." -ForegroundColor White
    }
    catch {
        Write-Host "  ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.ErrorDetails) {
            Write-Host "  Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
        }
    }
}

Write-Host "`n✅ Endpoint test complete!" -ForegroundColor Green
Write-Host "`nConclusion:" -ForegroundColor Cyan
Write-Host "  - If all tests passed: Backend is ready, uncomment extension code" -ForegroundColor White
Write-Host "  - If 422 errors: Backend doesn't support style_prefs yet" -ForegroundColor White
