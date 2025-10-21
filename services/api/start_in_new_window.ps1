# Start API server in a separate window (never auto-killed)
$scriptPath = Join-Path $PSScriptRoot "start_server.ps1"

Write-Host "Starting API server in new window..." -ForegroundColor Green
Write-Host "Location: $PSScriptRoot" -ForegroundColor Cyan

# Build the command to run in the new window
$command = "Set-Location '$PSScriptRoot'; & '$scriptPath'"

Start-Process powershell -ArgumentList "-NoExit","-Command",$command

Write-Host "`n✓ Server started in new window" -ForegroundColor Green
Write-Host "Wait ~10 seconds for startup, then run:" -ForegroundColor Yellow
Write-Host "  .\check_routes.ps1" -ForegroundColor White
