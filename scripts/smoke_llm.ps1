#!/usr/bin/env pwsh
# Smoke test for Ollama integration in production
# Tests the LLM provider directly inside the API container
#
# PRODUCTION VALIDATION:
# - Confirms API can reach infra-ollama-1:11434
# - Verifies llm_complete() returns ("text", "ollama") in prod
# - Warns if falling back to OpenAI or template
#
# SUCCESS CRITERIA:
# - Exit code 0 (even if using fallback)
# - backend="ollama" in production (expected)
# - backend="openai" or "template" = warning but not failure

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Ollama Integration Smoke Test" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if API container is running
$apiContainer = docker ps --filter "name=applylens-api-prod" --format "{{.Names}}"
if (-not $apiContainer) {
    Write-Host "❌ API container not running" -ForegroundColor Red
    exit 1
}

Write-Host "✓ API container running: $apiContainer" -ForegroundColor Green
Write-Host ""

# Test LLM provider via Python (using llm_complete function)
Write-Host "Testing LLM provider..." -ForegroundColor Yellow
$pythonScript = @'
import asyncio
import sys
import json
sys.path.insert(0, '/app')

from app.llm_provider import llm_complete

async def test():
    prompt = "Summarize mailbox status in one friendly sentence."

    text, backend = await llm_complete(prompt)

    # Output as JSON for parsing
    result = {
        "backend": backend,
        "text": text[:200] if text else ""
    }
    print(json.dumps(result))

    # Validate backend name
    if backend not in ["ollama", "openai", "template"]:
        print(f"ERROR: Invalid backend name: {backend}", file=sys.stderr)
        sys.exit(1)

    # Validate response
    if not text or len(text) < 10:
        print("ERROR: Response too short or empty", file=sys.stderr)
        sys.exit(1)

    # Warn if not using Ollama (expected in production)
    if backend != "ollama":
        print(f"⚠ WARNING: Using {backend} instead of ollama", file=sys.stderr)

asyncio.run(test())
'@

$result = docker exec $apiContainer python -c $pythonScript 2>&1
$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "Output:" -ForegroundColor Cyan

try {
    # Try to parse JSON output
    $jsonLine = $result | Where-Object { $_ -match '^\{.*\}$' } | Select-Object -First 1
    if ($jsonLine) {
        $parsed = $jsonLine | ConvertFrom-Json
        Write-Host "  Backend: $($parsed.backend)" -ForegroundColor $(if ($parsed.backend -eq "ollama") { "Green" } else { "Yellow" })
        Write-Host "  Response: $($parsed.text)" -ForegroundColor Gray
    } else {
        Write-Host $result
    }
} catch {
    Write-Host $result
}

Write-Host ""

if ($exitCode -eq 0) {
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "✅ Smoke test PASSED" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
} else {
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "❌ Smoke test FAILED" -ForegroundColor Red
    Write-Host "==========================================" -ForegroundColor Red
    exit 1
}
