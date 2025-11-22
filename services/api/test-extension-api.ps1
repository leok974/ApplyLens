# Smoke test for extension API endpoints
$BASE_URL = "http://localhost:8003"

Write-Host "`n🧪 Extension API Smoke Tests" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Gray

# Test 1: Profile endpoint
Write-Host "`n1️⃣  Testing GET /api/profile/me..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/api/profile/me" -Method Get
    Write-Host "✓ Profile retrieved successfully!" -ForegroundColor Green
    Write-Host "  Name: $($response.name)" -ForegroundColor White
    Write-Host "  Headline: $($response.headline)" -ForegroundColor White
    Write-Host "  Projects: $($response.projects.Count)" -ForegroundColor White
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

# Test 2: Log application
Write-Host "`n2️⃣  Testing POST /api/extension/applications..." -ForegroundColor Cyan
try {
    $appData = @{
        company = "Acme AI"
        role = "AI Engineer"
        job_url = "https://jobs.acme.ai/ai-engineer-123"
        notes = "dev smoke test"
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$BASE_URL/api/extension/applications" `
        -Method Post `
        -ContentType "application/json" `
        -Body $appData

    Write-Host "✓ Application logged successfully!" -ForegroundColor Green
    Write-Host "  ID: $($response.id)" -ForegroundColor White
    Write-Host "  OK: $($response.ok)" -ForegroundColor White
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

# Test 3: Log outreach
Write-Host "`n3️⃣  Testing POST /api/extension/outreach..." -ForegroundColor Cyan
try {
    $outreachData = @{
        company = "Acme AI"
        role = "AI Engineer"
        recruiter_name = "Jane Doe"
        recruiter_profile_url = "https://www.linkedin.com/in/janedoe"
        message_preview = "Hi Jane, great to connect..."
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$BASE_URL/api/extension/outreach" `
        -Method Post `
        -ContentType "application/json" `
        -Body $outreachData

    Write-Host "✓ Outreach logged successfully!" -ForegroundColor Green
    Write-Host "  ID: $($response.id)" -ForegroundColor White
    Write-Host "  OK: $($response.ok)" -ForegroundColor White
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

# Test 4: Generate form answers
Write-Host "`n4️⃣  Testing POST /api/extension/generate-form-answers..." -ForegroundColor Cyan
try {
    $formData = @{
        job = @{
            title = "Senior AI Engineer"
            company = "Acme AI"
        }
        fields = @(
            @{
                field_id = "experience"
                label = "Years of experience"
                type = "text"
            },
            @{
                field_id = "why_join"
                label = "Why do you want to join us?"
                type = "textarea"
            }
        )
    } | ConvertTo-Json -Depth 10

    $response = Invoke-RestMethod -Uri "$BASE_URL/api/extension/generate-form-answers" `
        -Method Post `
        -ContentType "application/json" `
        -Body $formData

    Write-Host "✓ Form answers generated successfully!" -ForegroundColor Green
    Write-Host "  Answers: $($response.answers.Count)" -ForegroundColor White
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

# Test 5: Generate recruiter DM
Write-Host "`n5️⃣  Testing POST /api/extension/generate-recruiter-dm..." -ForegroundColor Cyan
try {
    $dmData = @{
        profile = @{
            name = "Jane Doe"
            headline = "Engineering Manager at Acme AI"
            company = "Acme AI"
        }
        job = @{
            title = "Senior AI Engineer"
        }
    } | ConvertTo-Json -Depth 10

    $response = Invoke-RestMethod -Uri "$BASE_URL/api/extension/generate-recruiter-dm" `
        -Method Post `
        -ContentType "application/json" `
        -Body $dmData

    Write-Host "✓ Recruiter DM generated successfully!" -ForegroundColor Green
    Write-Host "  Message preview: $($response.message.Substring(0, [Math]::Min(50, $response.message.Length)))..." -ForegroundColor White
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host "`n" + "=" * 60 -ForegroundColor Gray
Write-Host "✅ Smoke tests completed!" -ForegroundColor Green
Write-Host ""
