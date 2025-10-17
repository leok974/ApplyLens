# Weekly Git History Sanity Check (PowerShell)
# Verifies no dbt artifacts have snuck back into remote history
# Run: .\analytics\ops\weekly-history-check.ps1

$ErrorActionPreference = "Stop"

Write-Host "🔍 Weekly Git History Sanity Check" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Fetch latest remote state
Write-Host "📡 Fetching latest remote refs..." -ForegroundColor Yellow
git fetch --all --quiet

# Check for dbt_packages in remote history
Write-Host "🔎 Scanning remote history for dbt_packages..." -ForegroundColor Yellow
$packagesCount = (git log --remotes --format=%H | 
  ForEach-Object { git ls-tree -r --name-only $_ 2>$null } |
  Select-String "dbt_packages" |
  Measure-Object).Count

# Check for package-lock.yml in remote history
Write-Host "🔎 Scanning remote history for package-lock.yml..." -ForegroundColor Yellow
$lockfileCount = (git log --remotes --format=%H |
  ForEach-Object { git ls-tree -r --name-only $_ 2>$null } |
  Select-String "package-lock.yml" |
  Measure-Object).Count

# Report results
Write-Host ""
Write-Host "📊 Results:" -ForegroundColor Cyan
Write-Host "  dbt_packages files:   $packagesCount"
Write-Host "  package-lock.yml:     $lockfileCount"
Write-Host ""

if ($packagesCount -eq 0 -and $lockfileCount -eq 0) {
  Write-Host "✅ History is clean! No artifacts found." -ForegroundColor Green
  Write-Host ""
  Write-Host "📅 Last checked: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")"
  exit 0
} else {
  Write-Host "❌ WARNING: Artifacts detected in history!" -ForegroundColor Red
  Write-Host ""
  Write-Host "🚨 Action Required:" -ForegroundColor Yellow
  Write-Host "  1. Identify which commit introduced them:"
  Write-Host "     git log --remotes --all -- '**/dbt_packages/**' '**/package-lock.yml'"
  Write-Host ""
  Write-Host "  2. Check if it's in a PR or feature branch"
  Write-Host "  3. Review docs/HISTORY-CLEANUP.md for remediation"
  Write-Host ""
  exit 1
}
