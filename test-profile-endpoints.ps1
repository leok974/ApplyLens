# Test Profile Analytics endpoints
$API_URL = "http://127.0.0.1:8003"
$USER = "leoklemet.pa@gmail.com"

Write-Host "`n=== Phase 2 Profile Analytics Test ===" -ForegroundColor Cyan

# 1. Rebuild profile
Write-Host "`n1. Rebuilding profile for $USER..." -ForegroundColor Yellow
$rebuild = Invoke-RestMethod -Uri "$API_URL/profile/rebuild?user_email=$USER&lookback_days=90" -Method Post
Write-Host "Emails processed: $($rebuild.emails_processed)"
Write-Host "Senders: $($rebuild.senders)"
Write-Host "Categories: $($rebuild.categories)"
Write-Host "Interests: $($rebuild.interests)"

# 2. Get profile summary
Write-Host "`n2. Getting profile summary..." -ForegroundColor Yellow
$summary = Invoke-RestMethod -Uri "$API_URL/profile/db-summary?user_email=$USER"

Write-Host "`nTop 5 Senders:"
$summary.top_senders | Select-Object -First 5 | ForEach-Object {
    Write-Host "  - $($_.domain): $($_.total) emails (open rate: $($_.open_rate)%)"
}

Write-Host "`nTop 5 Categories:"
$summary.categories | Select-Object -First 5 | ForEach-Object {
    Write-Host "  - $($_.category): $($_.total) emails"
}

Write-Host "`nTop 10 Interests:"
$summary.interests | Select-Object -First 10 | ForEach-Object {
    Write-Host "  - $($_.keyword) (score: $($_.score))"
}

# 3. Get category breakdown
Write-Host "`n3. Getting category breakdown..." -ForegroundColor Yellow
$categories = Invoke-RestMethod -Uri "$API_URL/profile/db-categories?user_email=$USER"
Write-Host "Total emails: $($categories.total_emails)"
foreach ($cat in $categories.categories) {
    Write-Host "  - $($cat.category): $($cat.total) ($($cat.percentage)%)"
}

Write-Host "`n=== Profile Analytics Test Complete ===" -ForegroundColor Green
