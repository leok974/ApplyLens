# SA Key Rotation Reminder Script
# Called by Windows Task Scheduler every 90 days
# Sends multiple notifications to ensure visibility

param(
    [string]$SlackWebhook = $env:SLACK_WEBHOOK  # Optional: set SLACK_WEBHOOK env var
)

$ErrorActionPreference = "Continue"

$message = "🔐 REMINDER: Rotate Service Account key for applylens-warehouse. See docs/HOUSEKEEPING-CHECKLIST.md for procedure."

# 1. Write to Windows Event Log (always works, even without interactive session)
try {
    Write-EventLog -LogName Application -Source "Windows PowerShell" -EntryType Information -EventId 9001 -Message $message
    Write-Host "✅ Logged to Windows Event Log (Event ID: 9001)" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Could not write to Event Log: $_" -ForegroundColor Yellow
}

# 2. Try to show popup (only works if user is logged in)
try {
    $result = msg $env:USERNAME /TIME:60 $message 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Popup message sent to user" -ForegroundColor Green
    } else {
        Write-Host "⚠️ No interactive session - popup skipped" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️ Could not send popup: $_" -ForegroundColor Yellow
}

# 3. Send Slack notification (if webhook configured)
if ($SlackWebhook) {
    try {
        $body = @{
            text = $message
            username = "ApplyLens Warehouse Monitor"
            icon_emoji = ":closed_lock_with_key:"
        } | ConvertTo-Json
        
        Invoke-RestMethod -Method Post -Uri $SlackWebhook -Body $body -ContentType "application/json" -ErrorAction Stop
        Write-Host "✅ Slack notification sent" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Could not send Slack notification: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "ℹ️ Slack webhook not configured (set SLACK_WEBHOOK env var)" -ForegroundColor Cyan
}

# 4. Write to log file (backup notification method)
$logPath = "$PSScriptRoot\..\..\logs\sa-key-rotation-reminders.log"
$logDir = Split-Path $logPath -Parent
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$logEntry = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $message"
Add-Content -Path $logPath -Value $logEntry
Write-Host "✅ Logged to file: $logPath" -ForegroundColor Green

# 5. Print summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "SA Key Rotation Reminder Sent!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next rotation due: ~3 months from now" -ForegroundColor Yellow
Write-Host "Procedure: docs/HOUSEKEEPING-CHECKLIST.md`n" -ForegroundColor Yellow

exit 0
