# Test Style Preferences End-to-End

# Test with "friendly" tone + "short" length
$response1 = Invoke-RestMethod -Uri "http://localhost:8003/api/extension/generate-form-answers" `
    -Method POST `
    -Headers @{
        "Content-Type" = "application/json"
        "X-Dev-Key" = "dev123"
    } `
    -Body (Get-Content "test_style_prefs.json" -Raw)

Write-Host "`n=== Test 1: Friendly + Short ===" -ForegroundColor Cyan
Write-Host $response1.answers.why_interested -ForegroundColor White

# Test with "confident" tone + "long" length
$payload2 = @{
    job = @{
        title = "Senior AI Engineer"
        company = "Anthropic"
        url = "https://www.anthropic.com/careers"
    }
    fields = @(
        @{
            field_id = "why_interested"
            semantic_key = "why_interested"
            label = "Why are you interested in this role?"
            type = "textarea"
        }
    )
    profile_context = @{
        name = "Leo Klemet"
        headline = "AI/ML Engineer · Agentic systems · Full-stack"
        experience_years = 5
        target_roles = @("AI Engineer", "Machine Learning Engineer")
        tech_stack = @("Python", "FastAPI", "React", "LLMs")
        work_setup = "Remote"
    }
    style_prefs = @{
        tone = "confident"
        length = "long"
    }
}

$response2 = Invoke-RestMethod -Uri "http://localhost:8003/api/extension/generate-form-answers" `
    -Method POST `
    -Headers @{
        "Content-Type" = "application/json"
        "X-Dev-Key" = "dev123"
    } `
    -Body ($payload2 | ConvertTo-Json -Depth 10)

Write-Host "`n=== Test 2: Confident + Long ===" -ForegroundColor Cyan
Write-Host $response2.answers.why_interested -ForegroundColor White

Write-Host "`n✅ Style preferences working!" -ForegroundColor Green
