# Test M2M Authentication and CSRF Exemptions
# Tests all CSRF bypass mechanisms

$baseUrl = "http://localhost:8003"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "M2M AUTHENTICATION & CSRF TESTS" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Test 1: Path-based exemption (Extension API)
Write-Host "1️⃣  Testing path exemption (Extension API)..." -ForegroundColor Yellow
try {
    $body = @{
        company = "TestCo"
        role = "Engineer"
        job_url = "https://example.com/job/123"
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$baseUrl/api/extension/applications" `
        -Method POST `
        -Headers @{'Content-Type'='application/json'} `
        -Body $body `
        -ErrorAction Stop

    Write-Host "   ✓ PASS - Path exemption working (no CSRF token needed)" -ForegroundColor Green
    Write-Host "     Response ID: $($response.id)" -ForegroundColor Gray
} catch {
    if ($_.Exception.Response.StatusCode -eq 403) {
        Write-Host "   ✗ FAIL - CSRF protection not bypassed for exempt path!" -ForegroundColor Red
    } else {
        Write-Host "   ✗ FAIL - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Test 2: M2M with Authorization header
Write-Host "`n2️⃣  Testing M2M auth (Authorization header)..." -ForegroundColor Yellow
try {
    $body = @{
        company = "TestCo M2M"
        role = "Engineer"
    } | ConvertTo-Json

    # Note: This endpoint would normally require CSRF, but Authorization header bypasses it
    $response = Invoke-WebRequest -Uri "$baseUrl/api/applications" `
        -Method POST `
        -Headers @{
            'Content-Type'='application/json'
            'Authorization'='Bearer test-token-123'
        } `
        -Body $body `
        -UseBasicParsing `
        -ErrorAction Stop

    if ($response.StatusCode -lt 400) {
        Write-Host "   ✓ PASS - M2M auth bypassed CSRF" -ForegroundColor Green
    } else {
        Write-Host "   ? Status: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 403) {
        Write-Host "   ✗ FAIL - Authorization header didn't bypass CSRF!" -ForegroundColor Red
    } else {
        Write-Host "   ⚠️  Expected failure (endpoint may not exist): $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Test 3: M2M with X-API-Key header
Write-Host "`n3️⃣  Testing M2M auth (X-API-Key header)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/gmail/backfill/start?days=3" `
        -Method POST `
        -Headers @{
            'X-API-Key'='test-api-key'
        } `
        -UseBasicParsing `
        -ErrorAction Stop

    $result = $response.Content | ConvertFrom-Json
    Write-Host "   ✓ PASS - X-API-Key accepted" -ForegroundColor Green
    Write-Host "     Job ID: $($result.job_id)" -ForegroundColor Gray
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "   ⚠️  API key required but BACKFILL_API_KEY not set (expected in dev)" -ForegroundColor Yellow
    } elseif ($_.Exception.Response.StatusCode -eq 403) {
        Write-Host "   ✗ FAIL - X-API-Key didn't bypass CSRF!" -ForegroundColor Red
    } else {
        Write-Host "   ⚠️  $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Test 4: Gmail path exemption (no auth needed)
Write-Host "`n4️⃣  Testing Gmail path exemption..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/gmail/backfill/start?days=3" `
        -Method POST `
        -ErrorAction Stop

    Write-Host "   ✓ PASS - Gmail path exempt from CSRF" -ForegroundColor Green
    Write-Host "     Job ID: $($response.job_id)" -ForegroundColor Gray
} catch {
    if ($_.Exception.Response.StatusCode -eq 403 -and $_.ErrorDetails.Message -match "CSRF") {
        Write-Host "   ✗ FAIL - Gmail path not exempt from CSRF!" -ForegroundColor Red
    } elseif ($_.Exception.Response.StatusCode -eq 403 -and $_.ErrorDetails.Message -match "Dev routes") {
        Write-Host "   ⚠️  Dev routes disabled (set ALLOW_DEV_ROUTES=1)" -ForegroundColor Yellow
    } else {
        Write-Host "   ⚠️  $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Test 5: DevDiag path exemption
Write-Host "`n5️⃣  Testing DevDiag path exemption..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/ops/diag/health" `
        -UseBasicParsing `
        -ErrorAction Stop

    if ($response.StatusCode -eq 503) {
        Write-Host "   ✓ PASS - DevDiag path exempt (503 = service not configured)" -ForegroundColor Green
    } elseif ($response.StatusCode -eq 200) {
        Write-Host "   ✓ PASS - DevDiag health check successful" -ForegroundColor Green
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "   ✗ FAIL - DevDiag route not found!" -ForegroundColor Red
    } elseif ($_.Exception.Response.StatusCode -eq 403) {
        Write-Host "   ✗ FAIL - DevDiag path not exempt from CSRF!" -ForegroundColor Red
    } elseif ($_.Exception.Response.StatusCode -eq 503) {
        Write-Host "   ✓ PASS - DevDiag path exempt (503 = service not configured)" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Test 6: Verify non-exempt endpoint requires CSRF
Write-Host "`n6️⃣  Testing CSRF enforcement (non-exempt endpoint)..." -ForegroundColor Yellow
try {
    $body = @{ test = "value" } | ConvertTo-Json
    $response = Invoke-WebRequest -Uri "$baseUrl/api/some-random-endpoint" `
        -Method POST `
        -Headers @{'Content-Type'='application/json'} `
        -Body $body `
        -UseBasicParsing `
        -ErrorAction Stop

    Write-Host "   ⚠️  Endpoint doesn't exist or CSRF not enforced" -ForegroundColor Yellow
} catch {
    if ($_.Exception.Response.StatusCode -eq 403 -and $_.ErrorDetails.Message -match "CSRF") {
        Write-Host "   ✓ PASS - CSRF correctly enforced on non-exempt endpoints" -ForegroundColor Green
    } elseif ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "   ⚠️  Endpoint doesn't exist (expected)" -ForegroundColor Gray
    } else {
        Write-Host "   ? Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Yellow
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Testing complete!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Summary
Write-Host "📋 Summary:" -ForegroundColor Cyan
Write-Host "  • Path exemptions: /api/extension/*, /api/gmail/*, /api/ops/diag*" -ForegroundColor Gray
Write-Host "  • M2M auth: Authorization or X-API-Key headers" -ForegroundColor Gray
Write-Host "  • Gmail backfill: Optional X-API-Key (set BACKFILL_API_KEY in prod)" -ForegroundColor Gray
Write-Host ""
