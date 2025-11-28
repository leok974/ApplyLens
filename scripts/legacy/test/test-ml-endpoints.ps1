# Test ML labeling endpoints
$API_URL = "http://127.0.0.1:8003"

Write-Host "`n=== Phase 2 ML Labeling System Test ===" -ForegroundColor Cyan

# 1. Check ML stats
Write-Host "`n1. Checking ML labeling stats..." -ForegroundColor Yellow
$stats = Invoke-RestMethod -Uri "$API_URL/api/ml/stats"
Write-Host "Total emails: $($stats.total_emails)"
Write-Host "Labeled emails: $($stats.labeled_emails)"
Write-Host "Coverage: $($stats.coverage)%"
Write-Host "Categories:" ($stats.categories | ConvertTo-Json -Compress)

# 2. Label recent emails
Write-Host "`n2. Labeling recent 100 emails..." -ForegroundColor Yellow
$rebuild = Invoke-RestMethod -Uri "$API_URL/api/ml/label/rebuild?limit=100" -Method Post
Write-Host "Updated: $($rebuild.updated) emails"
Write-Host "Categories:" ($rebuild.categories | ConvertTo-Json -Compress)

# 3. Preview promotions
Write-Host "`n3. Previewing promotions (limit 5)..." -ForegroundColor Yellow
$preview = Invoke-RestMethod -Uri "$API_URL/api/ml/label/preview?category=promotions&limit=5"
foreach ($email in $preview) {
    Write-Host "  - [$($email.category)] $($email.subject) (from: $($email.sender))"
}

# 4. Check stats again
Write-Host "`n4. Checking updated stats..." -ForegroundColor Yellow
$stats2 = Invoke-RestMethod -Uri "$API_URL/api/ml/stats"
Write-Host "Labeled emails: $($stats2.labeled_emails) (+$($stats2.labeled_emails - $stats.labeled_emails))"
Write-Host "Coverage: $($stats2.coverage)%"

Write-Host "`n=== ML Labeling Test Complete ===" -ForegroundColor Green
