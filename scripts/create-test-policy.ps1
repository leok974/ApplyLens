#!/usr/bin/env pwsh
# STATUS: unclear. Mentioned in REPO_AUDIT_PHASE1.md.
# If not used by 2025-12-31, move to scripts/legacy/.
<#
.SYNOPSIS
    Create a test policy that matches all emails (for demo/testing)

.DESCRIPTION
    Creates a simple policy that will match all emails in the database,
    allowing you to test the "Always do this" feature immediately.

    The policy:
    - Name: "Test: Label all emails"
    - Action: label_email
    - Condition: exists("email_id") - matches all emails
    - Priority: 50 (higher than learned policies at 40)
    - Confidence: 0.7

.EXAMPLE
    .\create-test-policy.ps1
#>

$ErrorActionPreference = "Stop"
$API_BASE = "http://localhost:8003/api"

Write-Host "=== Creating Test Policy ===" -ForegroundColor Cyan
Write-Host ""

# Create policy that matches ALL emails
$policy = @{
    name = "Test: Label all emails (FOR DEMO)"
    enabled = $true
    priority = 50
    action = "label_email"
    confidence_threshold = 0.7
    condition = @{
        exists = @("email_id")
    }
} | ConvertTo-Json -Depth 5

Write-Host "Creating policy that matches ALL emails..." -ForegroundColor Yellow
Write-Host ""

try {
    $result = Invoke-RestMethod -Uri "$API_BASE/actions/policies" `
        -Method POST `
        -ContentType "application/json" `
        -Body $policy

    Write-Host "✓ Policy created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  ID: $($result.id)" -ForegroundColor Gray
    Write-Host "  Name: $($result.name)" -ForegroundColor Gray
    Write-Host "  Action: $($result.action)" -ForegroundColor Gray
    Write-Host "  Priority: $($result.priority)" -ForegroundColor Gray
    Write-Host "  Enabled: $($result.enabled)" -ForegroundColor Gray
    Write-Host ""

    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Propose actions for emails:" -ForegroundColor Gray
    Write-Host "     `$body = @{ email_ids = @(1,2,3,4,5) } | ConvertTo-Json" -ForegroundColor DarkGray
    Write-Host "     curl -X POST $API_BASE/actions/propose -H 'Content-Type: application/json' -d `$body" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  2. View in tray:" -ForegroundColor Gray
    Write-Host "     curl $API_BASE/actions/tray" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  3. Or open UI:" -ForegroundColor Gray
    Write-Host "     http://localhost:5175" -ForegroundColor DarkGray
    Write-Host "     Click 'Actions' button → Try 'Always do this'" -ForegroundColor DarkGray
    Write-Host ""

    # Auto-propose for first 5 emails
    Write-Host "Auto-proposing for first 5 emails..." -ForegroundColor Yellow
    $proposeBody = @{ email_ids = @(1,2,3,4,5) } | ConvertTo-Json

    try {
        $proposed = Invoke-RestMethod -Uri "$API_BASE/actions/propose" `
            -Method POST `
            -ContentType "application/json" `
            -Body $proposeBody

        $count = $proposed.Count
        if ($count -gt 0) {
            Write-Host "✓ Created $count proposed action(s)" -ForegroundColor Green
            Write-Host ""
            Write-Host "Ready to test! Open:" -ForegroundColor Cyan
            Write-Host "  http://localhost:5175" -ForegroundColor White
            Write-Host ""
        } else {
            Write-Host "⚠ No actions proposed (emails might not exist yet)" -ForegroundColor Yellow
            Write-Host "  Sync emails first, then run propose command" -ForegroundColor Gray
        }
    } catch {
        Write-Host "⚠ Could not auto-propose: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "  Run propose command manually (see steps above)" -ForegroundColor Gray
    }

} catch {
    Write-Host "✗ Failed to create policy" -ForegroundColor Red
    Write-Host ""

    $errorMsg = $_.Exception.Message
    if ($_.ErrorDetails.Message) {
        try {
            $errorDetail = $_.ErrorDetails.Message | ConvertFrom-Json
            if ($errorDetail.detail) {
                $errorMsg = $errorDetail.detail
            }
        } catch {
            $errorMsg = $_.ErrorDetails.Message
        }
    }

    Write-Host "Error: $errorMsg" -ForegroundColor Red
    Write-Host ""

    # Check if API is running
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Is API running?" -ForegroundColor Gray
    Write-Host "     cd d:/ApplyLens/infra && docker compose ps api" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  2. Check API logs:" -ForegroundColor Gray
    Write-Host "     docker compose logs api --tail 20" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  3. Test API manually:" -ForegroundColor Gray
    Write-Host "     curl http://localhost:8003/docs" -ForegroundColor DarkGray
    Write-Host ""

    exit 1
}
