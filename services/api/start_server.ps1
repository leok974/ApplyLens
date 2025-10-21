# Rock-solid start script for ApplyLens API with Ollama integration
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# (optional) .\.venv\Scripts\Activate.ps1

# Minimal, stable env for demo
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONPATH       = "$PSScriptRoot"
$env:DATABASE_URL     = "sqlite:///./test.db"

# Turn off anything flaky for now
$env:ES_ENABLED                = "false"
$env:SCHEDULER_ENABLED         = "0"
$env:CREATE_TABLES_ON_STARTUP  = "false"

# Phase 4 flags + Ollama
$env:OLLAMA_BASE    = "http://localhost:11434"
$env:OLLAMA_MODEL   = "gpt-oss:20b"
$env:FEATURE_SUMMARIZE = "1"
$env:FEATURE_RAG_SEARCH = "1"

Write-Host "Starting API from $PWD" -ForegroundColor Green
Write-Host "Environment:" -ForegroundColor Cyan
Write-Host "  OLLAMA_BASE: $env:OLLAMA_BASE"
Write-Host "  OLLAMA_MODEL: $env:OLLAMA_MODEL"
Write-Host "  DATABASE_URL: $env:DATABASE_URL"
Write-Host "  ES_ENABLED: $env:ES_ENABLED"
Write-Host "  SCHEDULER_ENABLED: $env:SCHEDULER_ENABLED"
Write-Host ""
Write-Host "Press Ctrl+C to stop the server`n" -ForegroundColor Yellow

python -u -m uvicorn app.main:app `
  --host 127.0.0.1 `
  --port 8000 `
  --log-level info
