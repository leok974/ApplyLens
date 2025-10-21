# Email Risk v3.1 - Quick Smoke Test
# Creates a test risky email and fetches risk advice

$ES_URL = if ($env:ES_URL) { $env:ES_URL } else { "http://localhost:9200" }
$API_URL = if ($env:API_URL) { $env:API_URL } else { "http://localhost:8003" }

Write-Host "`n=== Email Risk v3.1 Smoke Test ===" -ForegroundColor Cyan

# Test document with multiple risk signals
$testDoc = @{
    id = "smoke-v31-adv"
    gmail_id = "smoke_001"
    thread_id = "thread_smoke"
    received_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    from = "hr@careers-finetunelearning.com"
    reply_to = "phisher@malicious-server.xyz"
    subject = "Urgent: Verify Your LinkedIn Profile"
    body_text = "Click here to update: https://bit.ly/urgentverify or open the attachment for instructions."
    headers_received_spf = "fail (google.com: domain does not designate sender)"
    headers_authentication_results = "spf=fail; dkim=fail; dmarc=fail"
    attachments = @(
        @{
            filename = "verify_account.docm"
            size = 156234
            mimetype = "application/vnd.ms-word.document.macroEnabled.12"
        }
    )
    labels_norm = @("inbox")
    source = "gmail"
} | ConvertTo-Json -Depth 5

Write-Host "1. Indexing test email through v3 pipeline..." -ForegroundColor Yellow

# Check if we're running inside Docker or outside
if (Test-Path "/proc/1/cgroup" -ErrorAction SilentlyContinue) {
    # Inside Docker container
    $indexResult = Invoke-RestMethod -Uri "$ES_URL/gmail_emails-999999/_doc/smoke-v31-adv?pipeline=applylens_emails_v3" `
        -Method Post `
        -ContentType "application/json" `
        -Body $testDoc
} else {
    # Outside Docker - use docker exec
    $tempFile = [System.IO.Path]::GetTempFileName()
    $testDoc | Out-File -FilePath $tempFile -Encoding UTF8
    docker cp $tempFile applylens-es-prod:/tmp/smoke_email.json | Out-Null
    $indexResult = docker exec applylens-es-prod curl -s -X POST `
        "http://localhost:9200/gmail_emails-999999/_doc/smoke-v31-adv?pipeline=applylens_emails_v3" `
        -H "Content-Type: application/json" `
        -d '@/tmp/smoke_email.json' | ConvertFrom-Json
    Remove-Item $tempFile
}

if ($indexResult.result -eq "created" -or $indexResult.result -eq "updated") {
    Write-Host "  ✓ Document indexed successfully" -ForegroundColor Green
} else {
    Write-Host "  ✗ Failed to index document" -ForegroundColor Red
    Write-Host $indexResult
    exit 1
}

Start-Sleep -Seconds 1

Write-Host "`n2. Fetching risk advice from API..." -ForegroundColor Yellow

# Test direct index parameter
$advice1 = Invoke-RestMethod -Uri "$API_URL/emails/smoke-v31-adv/risk-advice?index=gmail_emails-999999"

Write-Host "  ✓ Direct index query:" -ForegroundColor Green
Write-Host "    Score: $($advice1.suspicion_score)" -ForegroundColor White
Write-Host "    Suspicious: $($advice1.suspicious)" -ForegroundColor White
Write-Host "    Signals detected: $($advice1.explanations.Count)" -ForegroundColor White

if ($advice1.explanations.Count -gt 0) {
    Write-Host "`n  Explanations:" -ForegroundColor Cyan
    $advice1.explanations | ForEach-Object {
        Write-Host "    - $_" -ForegroundColor Gray
    }
}

Write-Host "`n3. Testing fallback search (without index param)..." -ForegroundColor Yellow

# Test fallback to wildcard search
$advice2 = Invoke-RestMethod -Uri "$API_URL/emails/smoke-v31-adv/risk-advice"

if ($advice2.suspicion_score -eq $advice1.suspicion_score) {
    Write-Host "  ✓ Fallback search working correctly" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Fallback returned different result" -ForegroundColor Yellow
}

Write-Host "`n4. Checking Prometheus metrics..." -ForegroundColor Yellow

$metrics = Invoke-RestMethod -Uri "$API_URL/metrics"
$served = ($metrics -split "`n" | Select-String "applylens_email_risk_served_total\{level=`"suspicious`"\}").ToString()

if ($served) {
    $count = ($served -split " ")[1]
    Write-Host "  ✓ Metric: $served" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Metric not found yet (may need more requests)" -ForegroundColor Yellow
}

Write-Host "`n=== Smoke Test Complete ===" -ForegroundColor Green
Write-Host "`nTest document: smoke-v31-adv"
Write-Host "Expected score: 66+ (SPF+DKIM+DMARC+ReplyTo+Shortener+Attachment)"
Write-Host "Actual score: $($advice1.suspicion_score)`n"

if ($advice1.suspicion_score -ge 40) {
    Write-Host "✅ PASS - Email correctly flagged as suspicious" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ FAIL - Email should be flagged as suspicious (score >= 40)" -ForegroundColor Red
    exit 1
}
