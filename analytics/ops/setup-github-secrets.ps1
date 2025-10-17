# Setup GitHub Actions Secrets for Warehouse Integration
# PowerShell version for Windows

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  GitHub Actions Secrets Setup" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Check if gh CLI is installed
if (!(Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Error: GitHub CLI (gh) is not installed" -ForegroundColor Red
    Write-Host "Install: https://cli.github.com/" -ForegroundColor Yellow
    exit 1
}

# Check if authenticated
try {
    gh auth status 2>&1 | Out-Null
} catch {
    Write-Host "Not authenticated to GitHub. Running login..." -ForegroundColor Yellow
    gh auth login
}

# Auto-detect repository
try {
    $repo = gh repo view --json nameWithOwner -q .nameWithOwner 2>&1
} catch {
    $repo = Read-Host "Could not auto-detect repository. Enter repository (owner/repo)"
}

Write-Host "Setting secrets for: $repo`n" -ForegroundColor Green

# 1. GCP_PROJECT
Write-Host "1. GCP_PROJECT" -ForegroundColor Yellow
$gcpProject = "applylens-gmail-1759983601"
Write-Host "   Value: $gcpProject"
gh secret set GCP_PROJECT --body $gcpProject --repo $repo
Write-Host "   ✓ Set`n" -ForegroundColor Green

# 2. GCP_SA_JSON
Write-Host "2. GCP_SA_JSON (Service Account Key)" -ForegroundColor Yellow
$saKeyPath = "D:\ApplyLens\secrets\applylens-warehouse-key.json"
if (!(Test-Path $saKeyPath)) {
    Write-Host "   Error: $saKeyPath not found" -ForegroundColor Red
    exit 1
}
Write-Host "   Reading from: $saKeyPath"
$saKeyContent = Get-Content $saKeyPath -Raw
gh secret set GCP_SA_JSON --body $saKeyContent --repo $repo
$fileSize = (Get-Item $saKeyPath).Length
Write-Host "   ✓ Set ($fileSize bytes)`n" -ForegroundColor Green

# 3. ES_URL
Write-Host "3. ES_URL (Elasticsearch URL)" -ForegroundColor Yellow
$esUrl = Read-Host "   Enter ES_URL (default: http://elasticsearch:9200)"
if ([string]::IsNullOrWhiteSpace($esUrl)) {
    $esUrl = "http://elasticsearch:9200"
}
Write-Host "   Value: $esUrl"
gh secret set ES_URL --body $esUrl --repo $repo
Write-Host "   ✓ Set`n" -ForegroundColor Green

# 4. PUSHGATEWAY_URL
Write-Host "4. PUSHGATEWAY_URL (Prometheus Pushgateway)" -ForegroundColor Yellow
$pushgatewayUrl = Read-Host "   Enter PUSHGATEWAY_URL (default: http://prometheus-pushgateway:9091)"
if ([string]::IsNullOrWhiteSpace($pushgatewayUrl)) {
    $pushgatewayUrl = "http://prometheus-pushgateway:9091"
}
Write-Host "   Value: $pushgatewayUrl"
gh secret set PUSHGATEWAY_URL --body $pushgatewayUrl --repo $repo
Write-Host "   ✓ Set`n" -ForegroundColor Green

# Summary
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Secrets configured:"
Write-Host "  ✓ GCP_PROJECT"
Write-Host "  ✓ GCP_SA_JSON"
Write-Host "  ✓ ES_URL"
Write-Host "  ✓ PUSHGATEWAY_URL`n"

Write-Host "Next steps:"
Write-Host "  1. Enable workflow: .github/workflows/dbt.yml"
Write-Host "  2. Trigger manually: gh workflow run dbt.yml"
Write-Host "  3. View runs: gh run list --workflow=dbt.yml`n"

Write-Host "Verify secrets:"
Write-Host "  gh secret list --repo $repo`n"
