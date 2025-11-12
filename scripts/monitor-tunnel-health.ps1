#!/usr/bin/env pwsh
# Simple health watcher for ApplyLens tunnel endpoints
# Usage: .\monitor-tunnel-health.ps1

Write-Host "Starting ApplyLens Tunnel Health Monitor..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

while($true){
  $t1 = curl.exe -s -o NUL -w "%{http_code}" https://applylens.app/
  $t2 = curl.exe -s -o NUL -w "%{http_code}" https://api.applylens.app/healthz

  $timestamp = Get-Date -Format "HH:mm:ss"

  # Color code based on status
  $webColor = if($t1 -eq "200") { "Green" } else { "Red" }
  $apiColor = if($t2 -eq "200") { "Green" } else { "Red" }

  Write-Host $timestamp -NoNewline
  Write-Host " web:" -NoNewline
  Write-Host $t1 -ForegroundColor $webColor -NoNewline
  Write-Host " api:" -NoNewline
  Write-Host $t2 -ForegroundColor $apiColor

  Start-Sleep 5
}
