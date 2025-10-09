# ApplyLens System Verification Script
# Run this to verify all components are working correctly

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ApplyLens System Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to infra directory
cd D:\ApplyLens\infra

# 1. Check health endpoints
Write-Host "[1/8] Checking health endpoints..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8003/healthz"
    $readiness = Invoke-RestMethod -Uri "http://localhost:8003/readiness"
    
    if ($health.ok -and $readiness.ok) {
        Write-Host "✓ Health: OK | Readiness: DB=$($readiness.db), ES=$($readiness.es)" -ForegroundColor Green
    } else {
        Write-Host "✗ Health check failed" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Cannot reach API: $_" -ForegroundColor Red
}

# 2. Check Gmail connection
Write-Host "[2/8] Checking Gmail connection..." -ForegroundColor Yellow
try {
    $status = Invoke-RestMethod -Uri "http://localhost:8003/gmail/status"
    if ($status.connected) {
        Write-Host "✓ Connected as $($status.user_email) | Emails: $($status.total)" -ForegroundColor Green
    } else {
        Write-Host "✗ Gmail not connected" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Cannot check Gmail status: $_" -ForegroundColor Red
}

# 3. Count emails in database
Write-Host "[3/8] Counting emails in Postgres..." -ForegroundColor Yellow
try {
    $emailCount = docker compose exec db psql -U postgres -d applylens -tAc "SELECT count(*) FROM emails;"
    Write-Host "✓ Emails in database: $emailCount" -ForegroundColor Green
} catch {
    Write-Host "✗ Cannot count emails: $_" -ForegroundColor Red
}

# 4. Count applications in database  
Write-Host "[4/8] Counting applications in Postgres..." -ForegroundColor Yellow
try {
    $appCount = docker compose exec db psql -U postgres -d applylens -tAc "SELECT count(*) FROM applications;"
    Write-Host "✓ Applications in database: $appCount" -ForegroundColor Green
} catch {
    Write-Host "✗ Cannot count applications: $_" -ForegroundColor Red
}

# 5. Count documents in Elasticsearch
Write-Host "[5/8] Counting documents in Elasticsearch..." -ForegroundColor Yellow
try {
    $esCount = (Invoke-RestMethod -Uri "http://localhost:9200/gmail_emails/_count").count
    Write-Host "✓ Documents in ES index: $esCount" -ForegroundColor Green
} catch {
    Write-Host "✗ Cannot count ES documents: $_" -ForegroundColor Red
}

# 6. Test search functionality
Write-Host "[6/8] Testing search functionality..." -ForegroundColor Yellow
try {
    $searchResults = Invoke-RestMethod -Uri "http://localhost:8003/search?q=Interview"
    $hitCount = $searchResults.hits.Count
    Write-Host "✓ Search working | 'Interview' results: $hitCount" -ForegroundColor Green
} catch {
    Write-Host "✗ Search failed: $_" -ForegroundColor Red
}

# 7. Check scheduled task
Write-Host "[7/8] Checking scheduled sync task..." -ForegroundColor Yellow
try {
    $task = Get-ScheduledTask -TaskName "ApplyLens-GmailSync" -ErrorAction Stop
    $taskInfo = Get-ScheduledTaskInfo -TaskName "ApplyLens-GmailSync"
    
    Write-Host "✓ Task: $($task.State) | Last run: $($taskInfo.LastRunTime) | Next run: $($taskInfo.NextRunTime)" -ForegroundColor Green
    
    if ($taskInfo.LastTaskResult -ne 0) {
        Write-Host "  ⚠ Last task result: $($taskInfo.LastTaskResult) (non-zero)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Scheduled task not found or cannot be accessed" -ForegroundColor Red
}

# 8. Check indexes
Write-Host "[8/8] Verifying database indexes..." -ForegroundColor Yellow
try {
    $indexes = docker compose exec db psql -U postgres -d applylens -tAc "SELECT indexname FROM pg_indexes WHERE tablename IN ('emails', 'applications') AND indexname LIKE 'idx_%';"
    $indexList = $indexes -split "`n" | Where-Object { $_ -ne "" }
    Write-Host "✓ Custom indexes found: $($indexList.Count)" -ForegroundColor Green
    foreach ($idx in $indexList) {
        Write-Host "  - $idx" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Cannot check indexes: $_" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Verification Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Quick access:" -ForegroundColor White
Write-Host "  • Inbox:   http://localhost:5175/inbox" -ForegroundColor Cyan
Write-Host "  • Tracker: http://localhost:5175/tracker" -ForegroundColor Cyan
Write-Host "  • API:     http://localhost:8003/docs" -ForegroundColor Cyan
Write-Host "  • Kibana:  http://localhost:5601" -ForegroundColor Cyan
Write-Host ""
