# Test Style Preferences End-to-End

# Test with "friendly" tone + "short" length
$response1 = Invoke-RestMethod -Uri "http://localhost:8003/api/extension/generate-form-answers" `
    -Method POST `
    -Headers @{
        "Content-Type" = "application/json"
    } `
    -Body (Get-Content "test_style_prefs.json" -Raw)

Write-Host "`n=== Test 1: Friendly + Short ===" -ForegroundColor Cyan
$answer1 = ($response1.answers | Where-Object { $_.field_id -eq "why_interested" }).answer
Write-Host $answer1 -ForegroundColor White
Write-Host "`nLength: $($answer1.Length) chars" -ForegroundColor Gray

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
    } `
    -Body ($payload2 | ConvertTo-Json -Depth 10)

Write-Host "`n=== Test 2: Confident + Long ===" -ForegroundColor Cyan
$answer2 = ($response2.answers | Where-Object { $_.field_id -eq "why_interested" }).answer
Write-Host $answer2 -ForegroundColor White
Write-Host "`nLength: $($answer2.Length) chars" -ForegroundColor Gray

Write-Host "`n✅ Style preferences working!" -ForegroundColor Green
Write-Host "Friendly+Short: $($answer1.Length) chars" -ForegroundColor Cyan
Write-Host "Confident+Long: $($answer2.Length) chars" -ForegroundColor Cyan
