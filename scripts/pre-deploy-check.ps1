# Pre-Deployment Validation Script (PowerShell)
# Ensures critical environment variables are set before deployment

param(
    [string]$EnvFile = ".env"
)

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "🔍 Pre-Deployment Validation" -ForegroundColor Cyan
Write-Host "=========================================`n" -ForegroundColor Cyan

$Errors = 0

# Load .env file if it exists
if (Test-Path $EnvFile) {
    Write-Host "📄 Loading environment from: $EnvFile" -ForegroundColor Gray
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
    Write-Host ""
}

# Function to check environment variable
function Test-EnvVar {
    param(
        [string]$VarName,
        [bool]$Required = $true,
        [bool]$Masked = $false
    )
    
    $value = [Environment]::GetEnvironmentVariable($VarName)
    
    if ($value) {
        if ($Masked) {
            Write-Host "✓ $VarName`: [MASKED]" -ForegroundColor Green
        } else {
            Write-Host "✓ $VarName`: $value" -ForegroundColor Green
        }
    } else {
        if ($Required) {
            Write-Host "✗ $VarName`: MISSING (required)" -ForegroundColor Red
            $script:Errors++
        } else {
            Write-Host "⚠ $VarName`: not set (optional)" -ForegroundColor Yellow
        }
    }
}

Write-Host "🔐 Security Configuration" -ForegroundColor Cyan
Write-Host "-------------------------"
Test-EnvVar "APPLYLENS_AES_KEY_BASE64" $true $true
Test-EnvVar "CSRF_SECRET_KEY" $true $true
Test-EnvVar "OAUTH_STATE_SECRET" $true $true
Test-EnvVar "HMAC_SECRET" $false $true  # Optional - used by Kibana, in infra/.env

Write-Host "`n🗄️  Database Configuration" -ForegroundColor Cyan
Write-Host "-------------------------"
Test-EnvVar "DATABASE_URL" $true $false
Test-EnvVar "POSTGRES_PASSWORD" $true $true

Write-Host "`n🔍 Search & Analytics" -ForegroundColor Cyan
Write-Host "-------------------------"
Test-EnvVar "ES_URL" $true $false
Test-EnvVar "ES_ENABLED" $true $false

Write-Host "`n🔑 OAuth Configuration" -ForegroundColor Cyan
Write-Host "-------------------------"
Test-EnvVar "GOOGLE_CLIENT_ID" $true $false
Test-EnvVar "GOOGLE_CLIENT_SECRET" $true $true
Test-EnvVar "GOOGLE_REDIRECT_URI" $true $false

Write-Host "`n📊 Monitoring (Optional)" -ForegroundColor Cyan
Write-Host "-------------------------"
Test-EnvVar "PROMETHEUS_ENABLED" $false $false
Test-EnvVar "RECAPTCHA_ENABLED" $false $false

Write-Host "`n=========================================" -ForegroundColor Cyan

if ($Errors -gt 0) {
    Write-Host "❌ Validation Failed: $Errors error(s) found`n" -ForegroundColor Red
    Write-Host "💡 Fix required:" -ForegroundColor Yellow
    Write-Host "   - Ensure all required environment variables are set"
    Write-Host "   - Check .env file or CI/CD secrets configuration"
    Write-Host "   - For AES key: run 'python scripts/generate_aes_key.py'"
    Write-Host ""
    exit 1
} else {
    Write-Host "✅ All validation checks passed!`n" -ForegroundColor Green
    Write-Host "🚀 Ready for deployment`n"
    exit 0
}
