$root = Split-Path $MyInvocation.MyCommand.Path -Parent
Set-Location $root
$dest = Join-Path $root "dist"
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
New-Item $dest -ItemType Directory | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zip = Join-Path $dest "applylens-companion-$stamp.zip"

# Exclude tests & local-only files
$include = @(
  "manifest.json","config.js","sw.js","content.js",
  "popup.html","popup.js","sidepanel.html","sidepanel.js",
  "icons","public","docs","store-listing.json",
  "LICENSE","README.md"
)

# Check if all files exist before packing
$missing = @()
foreach ($item in $include) {
    if (-not (Test-Path $item)) {
        $missing += $item
    }
}

if ($missing.Length -gt 0) {
    Write-Host "Warning: The following files are missing and will be skipped:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
}

# Filter to only existing items
$existing = $include | Where-Object { Test-Path $_ }

if ($existing.Length -eq 0) {
    Write-Host "Error: No files to pack!" -ForegroundColor Red
    exit 1
}

Compress-Archive -Path $existing -DestinationPath $zip
Write-Host "✅ Packed → $zip" -ForegroundColor Green
Write-Host "   Files included: $($existing.Length)" -ForegroundColor Cyan
Write-Host "   Size: $([math]::Round((Get-Item $zip).Length / 1KB, 2)) KB" -ForegroundColor Cyan
