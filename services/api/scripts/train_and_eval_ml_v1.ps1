#!/usr/bin/env pwsh
<#
.SYNOPSIS
    One-command training and evaluation for email classifier ML model.

.DESCRIPTION
    This script runs the complete ML training workflow:
    1. (Optional) Bootstrap training labels from existing emails
    2. Train ml_v1 model using TF-IDF + LogisticRegression
    3. Evaluate on golden set (if available)
    4. Print summary of artifacts and next steps

.PARAMETER Bootstrap
    Run bootstrap script before training (optional, default: false)

.PARAMETER Limit
    Limit for bootstrap script (default: 5000)

.EXAMPLE
    .\train_and_eval_ml_v1.ps1
    # Train using existing labels

.EXAMPLE
    .\train_and_eval_ml_v1.ps1 -Bootstrap -Limit 2000
    # Bootstrap 2000 labels first, then train
#>

param(
    [switch]$Bootstrap,
    [int]$Limit = 5000
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Email Classifier ML Training Pipeline" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to API directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiDir = Split-Path -Parent $scriptDir
Push-Location $apiDir

try {
    # Step 1: Optional bootstrap
    if ($Bootstrap) {
        Write-Host "[1/3] Bootstrapping training labels (limit: $Limit)..." -ForegroundColor Yellow
        python -m scripts.bootstrap_email_training_labels --limit $Limit

        if ($LASTEXITCODE -ne 0) {
            throw "Bootstrap script failed with exit code $LASTEXITCODE"
        }

        Write-Host "✅ Bootstrap complete" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "[1/3] Skipping bootstrap (using existing labels)" -ForegroundColor Gray
        Write-Host "     Use -Bootstrap flag to regenerate labels" -ForegroundColor Gray
        Write-Host ""
    }

    # Step 2: Train ML model
    Write-Host "[2/3] Training ml_v1 model..." -ForegroundColor Yellow
    python -m scripts.train_email_classifier

    if ($LASTEXITCODE -ne 0) {
        throw "Training script failed with exit code $LASTEXITCODE"
        }

    Write-Host "✅ Training complete" -ForegroundColor Green
    Write-Host ""

    # Step 3: Evaluate on golden set
    Write-Host "[3/3] Evaluating on golden set..." -ForegroundColor Yellow
    python -m scripts.eval_email_classifier_on_golden

    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️ Evaluation failed (golden set may be empty)" -ForegroundColor Yellow
        Write-Host "   This is OK if you haven't created hand-labeled data yet" -ForegroundColor Gray
    } else {
        Write-Host "✅ Evaluation complete" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Training Complete!" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📦 Artifacts saved to:" -ForegroundColor White
    Write-Host "   - models/email_opp_model.joblib" -ForegroundColor Gray
    Write-Host "   - models/email_opp_vectorizer.joblib" -ForegroundColor Gray
    Write-Host ""
    Write-Host "🔜 Next steps:" -ForegroundColor White
    Write-Host "   1. Review training metrics above" -ForegroundColor Gray
    Write-Host "   2. Deploy in ml_shadow mode:" -ForegroundColor Gray
    Write-Host "      EMAIL_CLASSIFIER_MODE=ml_shadow" -ForegroundColor DarkGray
    Write-Host "   3. Monitor agreement rate for 1-2 weeks" -ForegroundColor Gray
    Write-Host "   4. Switch to ml_live when metrics are green" -ForegroundColor Gray
    Write-Host ""
    Write-Host "📚 See docs/ML_TRAINING_EVALUATION_PLAN.md for details" -ForegroundColor White
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}
