# Test script for extension endpoints
# Run this after starting the server with Ctrl+Shift+B

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "EXTENSION ENDPOINTS TEST SUITE" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

$baseUrl = "http://localhost:8003"
$allPassed = $true

# Test 1: Profile endpoint (GET)
Write-Host "Test 1: GET /api/profile/me" -ForegroundColor Cyan
try {
    $profile = Invoke-RestMethod -Uri "$baseUrl/api/profile/me" -Method GET -ErrorAction Stop
    Write-Host "  ✓ PASS - Profile retrieved" -ForegroundColor Green
    Write-Host "    Name: $($profile.name)" -ForegroundColor Gray
    Write-Host "    Projects: $($profile.projects.Count)" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ FAIL - $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

# Test 2: Log application (POST)
Write-Host "`nTest 2: POST /api/extension/applications" -ForegroundColor Cyan
$appPayload = @{
    company = "TestCorp"
    role = "Senior AI Engineer"
    job_url = "https://example.com/jobs/123"
    notes = "Test from PowerShell"
} | ConvertTo-Json

try {
    $result = Invoke-RestMethod -Uri "$baseUrl/api/extension/applications" `
        -Method POST `
        -Headers @{'Content-Type'='application/json'} `
        -Body $appPayload `
        -ErrorAction Stop
    Write-Host "  ✓ PASS - Application logged" -ForegroundColor Green
    Write-Host "    ID: $($result.id)" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ FAIL - $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "    Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
    $allPassed = $false
}

# Test 3: Log outreach (POST)
Write-Host "`nTest 3: POST /api/extension/outreach" -ForegroundColor Cyan
$outreachPayload = @{
    company = "TechStartup"
    role = "ML Engineer"
    recruiter_name = "Jane Doe"
    recruiter_profile_url = "https://linkedin.com/in/janedoe"
    message_preview = "I found your profile interesting..."
} | ConvertTo-Json

try {
    $result = Invoke-RestMethod -Uri "$baseUrl/api/extension/outreach" `
        -Method POST `
        -Headers @{'Content-Type'='application/json'} `
        -Body $outreachPayload `
        -ErrorAction Stop
    Write-Host "  ✓ PASS - Outreach logged" -ForegroundColor Green
    Write-Host "    ID: $($result.id)" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ FAIL - $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "    Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
    $allPassed = $false
}

# Test 4: Generate form answers (POST)
Write-Host "`nTest 4: POST /api/extension/generate-form-answers" -ForegroundColor Cyan
$formPayload = @{
    job = @{
        title = "Senior AI Engineer"
        company = "TestCorp"
    }
    fields = @(
        @{ field_id = "years_exp"; label = "Years of Experience"; type = "number" }
        @{ field_id = "cover_letter"; label = "Cover Letter"; type = "textarea" }
    )
} | ConvertTo-Json -Depth 5

try {
    $result = Invoke-RestMethod -Uri "$baseUrl/api/extension/generate-form-answers" `
        -Method POST `
        -Headers @{'Content-Type'='application/json'} `
        -Body $formPayload `
        -ErrorAction Stop
    Write-Host "  ✓ PASS - Form answers generated" -ForegroundColor Green
    Write-Host "    Answers: $($result.answers.Count)" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ FAIL - $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "    Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
    $allPassed = $false
}

# Test 5: Generate recruiter DM (POST)
Write-Host "`nTest 5: POST /api/extension/generate-recruiter-dm" -ForegroundColor Cyan
$dmPayload = @{
    profile = @{
        name = "Jane Recruiter"
        headline = "Senior Technical Recruiter"
        company = "TechCorp"
    }
    job = @{
        title = "AI/ML Engineer"
    }
} | ConvertTo-Json -Depth 5

try {
    $result = Invoke-RestMethod -Uri "$baseUrl/api/extension/generate-recruiter-dm" `
        -Method POST `
        -Headers @{'Content-Type'='application/json'} `
        -Body $dmPayload `
        -ErrorAction Stop
    Write-Host "  ✓ PASS - DM generated" -ForegroundColor Green
    Write-Host "    Preview: $($result.message.Substring(0, [Math]::Min(50, $result.message.Length)))..." -ForegroundColor Gray
} catch {
    Write-Host "  ✗ FAIL - $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "    Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
    $allPassed = $false
}

# Test 6: Check Prometheus metrics
Write-Host "`nTest 6: Verify Prometheus metrics" -ForegroundColor Cyan
try {
    $metrics = Invoke-WebRequest -Uri "$baseUrl/metrics" -UseBasicParsing
    $extensionMetrics = ($metrics.Content -split "`n") | Select-String "extension"
    $csrfFailMetrics = ($metrics.Content -split "`n") | Select-String "csrf_fail.*extension"

    Write-Host "  ✓ PASS - Metrics endpoint accessible" -ForegroundColor Green
    Write-Host "    Extension metrics found: $($extensionMetrics.Count)" -ForegroundColor Gray

    if ($csrfFailMetrics.Count -gt 0) {
        Write-Host "    ⚠ WARNING: CSRF failures detected for extension endpoints:" -ForegroundColor Yellow
        $csrfFailMetrics | ForEach-Object { Write-Host "      $_" -ForegroundColor Yellow }
    } else {
        Write-Host "    ✓ No CSRF failures for extension endpoints" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ FAIL - $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

# Summary
Write-Host "`n========================================" -ForegroundColor Green
if ($allPassed) {
    Write-Host "✅ ALL TESTS PASSED" -ForegroundColor Green
} else {
    Write-Host "⚠️  SOME TESTS FAILED" -ForegroundColor Yellow
}
Write-Host "========================================`n" -ForegroundColor Green
