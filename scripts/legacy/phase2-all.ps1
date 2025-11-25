# Phase 2 PowerShell Automation Script
# Runs: Export -> Train -> Apply Labels workflow

param(
    [string]$EsUrl = "http://localhost:9200",
    [string]$EsIndex = "emails_v1-000001",
    [int]$Days = 60,
    [int]$Limit = 40000,
    [int]$PerCat = 8000,
    [string]$Weak = "$env:TEMP\weak_labels.jsonl",
    [string]$Model = "services/api/app/labeling/label_model.joblib",
    [string]$ApiBase = "http://localhost:8003"
)

Write-Host ""
Write-Host "╔═══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  ApplyLens Phase-2 Labeling Pipeline     ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Configuration
$env:ES_URL = $EsUrl
$env:ES_EMAIL_INDEX = $EsIndex

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  ES URL:        $EsUrl"
Write-Host "  ES Index:      $EsIndex"
Write-Host "  Days:          $Days"
Write-Host "  Limit:         $Limit"
Write-Host "  Per Category:  $PerCat"
Write-Host "  Output JSONL:  $Weak"
Write-Host "  Model Output:  $Model"
Write-Host "  API Base:      $ApiBase"
Write-Host ""

# Step 1: Export weak labels
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Step 1: Exporting Weak Labels" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

try {
    python services/api/app/labeling/export_weak_labels.py `
        --days $Days `
        --limit $Limit `
        --limit-per-cat $PerCat `
        --out $Weak

    if ($LASTEXITCODE -ne 0) {
        throw "Export failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "✅ Export complete!" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "❌ Export failed: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Train model
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Step 2: Training Model" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

try {
    python services/api/app/labeling/train_ml.py $Weak $Model

    if ($LASTEXITCODE -ne 0) {
        throw "Training failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "✅ Training complete!" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "❌ Training failed: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Apply labels
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Step 3: Applying Labels" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

try {
    $response = Invoke-RestMethod `
        -Uri "$ApiBase/labels/apply" `
        -Method POST `
        -Body '{}' `
        -ContentType 'application/json' `
        -ErrorAction Stop

    Write-Host ""
    Write-Host "✅ Labels applied!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Results:" -ForegroundColor Yellow
    $response | ConvertTo-Json -Depth 5 | Write-Host
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "❌ Apply failed: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Show statistics
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Statistics" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "To view statistics, run:" -ForegroundColor Yellow
Write-Host "  curl `"$ApiBase/labels/stats`" | jq" -ForegroundColor Gray
Write-Host "  curl `"$ApiBase/pr0file/summary?days=60`" | jq  # (replace 0 with o)" -ForegroundColor Gray
Write-Host ""

# Summary
Write-Host "╔═══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ Phase-2 Pipeline Complete!            ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Review statistics with curl commands above"
Write-Host "  2. Check Kibana dashboards"
Write-Host "  3. View API docs at: $ApiBase/docs"
Write-Host ""
Write-Host "Files Created:" -ForegroundColor Yellow
Write-Host "  JSONL: $Weak"
Write-Host "  Model: $Model"
Write-Host ""
