# Fivetran OAuth Verification - PowerShell Wrapper
# 
# Usage:
#   .\scripts\fivetran\verify_oauth.ps1 -ApiKey "xxx" -ApiSecret "yyy" -ConnectorId "zzz"
#
# Or set environment variables:
#   $env:FIVETRAN_API_KEY = "xxx"
#   $env:FIVETRAN_API_SECRET = "yyy"
#   $env:FIVETRAN_CONNECTOR_ID = "zzz"
#   .\scripts\fivetran\verify_oauth.ps1

param(
    [string]$ApiKey = $env:FIVETRAN_API_KEY,
    [string]$ApiSecret = $env:FIVETRAN_API_SECRET,
    [string]$ConnectorId = $env:FIVETRAN_CONNECTOR_ID
)

# Validate inputs
if (-not $ApiKey -or -not $ApiSecret -or -not $ConnectorId) {
    Write-Host "❌ Missing required parameters or environment variables!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Required:" -ForegroundColor Yellow
    Write-Host "  -ApiKey (or FIVETRAN_API_KEY env var)"
    Write-Host "  -ApiSecret (or FIVETRAN_API_SECRET env var)"
    Write-Host "  -ConnectorId (or FIVETRAN_CONNECTOR_ID env var)"
    Write-Host ""
    Write-Host "Usage Option 1 (Parameters):" -ForegroundColor Cyan
    Write-Host '  .\scripts\fivetran\verify_oauth.ps1 -ApiKey "xxx" -ApiSecret "yyy" -ConnectorId "zzz"'
    Write-Host ""
    Write-Host "Usage Option 2 (Environment Variables):" -ForegroundColor Cyan
    Write-Host '  $env:FIVETRAN_API_KEY = "your_key"'
    Write-Host '  $env:FIVETRAN_API_SECRET = "your_secret"'
    Write-Host '  $env:FIVETRAN_CONNECTOR_ID = "connector_id"'
    Write-Host '  .\scripts\fivetran\verify_oauth.ps1'
    Write-Host ""
    Write-Host "Usage Option 3 (npm script):" -ForegroundColor Cyan
    Write-Host "  npm run verify:fivetran:oauth"
    Write-Host ""
    exit 1
}

# Set environment variables for Node script
$env:FIVETRAN_API_KEY = $ApiKey
$env:FIVETRAN_API_SECRET = $ApiSecret
$env:FIVETRAN_CONNECTOR_ID = $ConnectorId

# Run Node.js verifier
Write-Host "🚀 Running Fivetran OAuth verifier..." -ForegroundColor Cyan
Write-Host ""

node scripts/fivetran/verify_oauth.mjs

# Capture exit code
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "✅ Verification complete! Check the evidence file:" -ForegroundColor Green
    Write-Host "   docs/hackathon/EVIDENCE_FIVETRAN_OAUTH.md" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "⚠️  Verification completed with issues. Review output above." -ForegroundColor Yellow
    Write-Host ""
}

exit $exitCode
