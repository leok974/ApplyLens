# Start ApplyLens API in dev mode with extension support
$env:APPLYLENS_DEV = "1"
$env:DATABASE_URL = "sqlite:///./dev_extension.db"
$env:CORS_ALLOW_ORIGINS = "http://localhost:5175,http://localhost:3000"

Write-Host "🚀 Starting ApplyLens API in DEV mode..." -ForegroundColor Green
Write-Host "   APPLYLENS_DEV=1" -ForegroundColor Cyan
Write-Host "   DATABASE_URL=$env:DATABASE_URL" -ForegroundColor Cyan
Write-Host ""
Write-Host "📡 Extension endpoints enabled:" -ForegroundColor Yellow
Write-Host "   GET  /api/profile/me" -ForegroundColor White
Write-Host "   POST /api/extension/applications" -ForegroundColor White
Write-Host "   POST /api/extension/outreach" -ForegroundColor White
Write-Host "   POST /api/extension/generate-form-answers" -ForegroundColor White
Write-Host "   POST /api/extension/generate-recruiter-dm" -ForegroundColor White
Write-Host ""

Set-Location d:\ApplyLens\services\api
uvicorn app.main:app --reload --port 8003
