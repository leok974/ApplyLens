# ApplyLens Gmail Backfill Check Script
# STATUS: unclear. Mentioned in REPO_AUDIT_PHASE1.md.
# If not used by 2025-12-31, move to scripts/legacy/.
# Runs backfill and shows Windows toast notification on failure

try {
    $resp = Invoke-WebRequest -Uri "http://localhost:8003/gmail/backfill?days=2" -Method POST -UseBasicParsing -TimeoutSec 30

    if ($resp.StatusCode -ge 400) {
        throw "HTTP $($resp.StatusCode)"
    }

    # Success - log it
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] ApplyLens backfill successful"

} catch {
    # Failure - show toast notification
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $errorMsg = "ApplyLens backfill failed: $_"

    # Log to file
    $logPath = Join-Path $PSScriptRoot "backfill-errors.log"
    Add-Content -Path $logPath -Value "[$timestamp] $errorMsg"

    # Show Windows message box
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($errorMsg, "ApplyLens Gmail Sync", 0, "Error") | Out-Null

    # Exit with error code
    exit 1
}
