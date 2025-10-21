# Diagnostic script for ApplyLens API startup issues

Write-Host "`n=== ApplyLens API Diagnostics ===" -ForegroundColor Green

# 1. Port conflict check
Write-Host "`n1. Checking port 8000..." -ForegroundColor Cyan
$portInUse = netstat -ano | Select-String ":8000" | Select-Object -First 1
if ($portInUse) {
    Write-Host "   ⚠ Port 8000 is in use:" -ForegroundColor Yellow
    Write-Host "   $portInUse" -ForegroundColor Gray
    
    # Extract PID
    if ($portInUse -match "\s+(\d+)\s*$") {
        $procId = $Matches[1]
        try {
            $process = Get-Process -Id $procId -ErrorAction Stop
            Write-Host "   Process: $($process.ProcessName) (PID: $procId)" -ForegroundColor Gray
            Write-Host "   To kill: Stop-Process -Id $procId -Force" -ForegroundColor Yellow
        } catch {
            Write-Host "   Could not get process details for PID $procId" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "   ✓ Port 8000 is available" -ForegroundColor Green
}

# 2. Current directory check
Write-Host "`n2. Checking current directory..." -ForegroundColor Cyan
$expectedPath = "d:\ApplyLens\services\api"
$currentPath = Get-Location
if ($currentPath.Path -eq $expectedPath) {
    Write-Host "   ✓ In correct directory: $currentPath" -ForegroundColor Green
} else {
    Write-Host "   ⚠ Not in expected directory" -ForegroundColor Yellow
    Write-Host "   Current:  $currentPath" -ForegroundColor Gray
    Write-Host "   Expected: $expectedPath" -ForegroundColor Gray
    Write-Host "   Fix: cd $expectedPath" -ForegroundColor Yellow
}

# 3. Check if app module exists
Write-Host "`n3. Checking app module..." -ForegroundColor Cyan
if (Test-Path ".\app\main.py") {
    Write-Host "   ✓ app\main.py exists" -ForegroundColor Green
    
    # Check for Phase 4 code
    $hasPhase4 = Select-String -Path ".\app\main.py" -Pattern "Phase 4 AI Features" -Quiet
    if ($hasPhase4) {
        Write-Host "   ✓ Phase 4 AI code present" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Phase 4 AI code not found" -ForegroundColor Red
    }
} else {
    Write-Host "   ✗ app\main.py not found" -ForegroundColor Red
}

# 4. Check Ollama service
Write-Host "`n4. Checking Ollama service..." -ForegroundColor Cyan

# Check if Ollama process is running
$ollamaProcess = Get-Process ollama* -ErrorAction SilentlyContinue
if ($ollamaProcess) {
    Write-Host "   ✓ Ollama process is running (PID: $($ollamaProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "   ✗ Ollama process not found" -ForegroundColor Red
    Write-Host "   Start with: ollama serve" -ForegroundColor Yellow
}

# Check if Ollama is listening on port 11434
$ollamaPort = netstat -ano | Select-String ":11434" | Select-Object -First 1
if ($ollamaPort) {
    Write-Host "   ✓ Ollama is listening on port 11434" -ForegroundColor Green
} else {
    Write-Host "   ⚠ Port 11434 not in use" -ForegroundColor Yellow
}

# Try to connect to Ollama
try {
    $ollama = curl.exe -s --max-time 5 http://localhost:11434/api/tags | ConvertFrom-Json
    Write-Host "   ✓ Ollama API is responding" -ForegroundColor Green
    Write-Host "   Models available:" -ForegroundColor Gray
    foreach ($model in $ollama.models) {
        $size = [math]::Round($model.size / 1GB, 2)
        Write-Host "     - $($model.name) ($size GB)" -ForegroundColor Gray
    }
    
    # Check for expected model
    $expectedModel = "gpt-oss:20b"
    if ($ollama.models.name -contains $expectedModel) {
        Write-Host "   ✓ Expected model '$expectedModel' is available" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ Expected model '$expectedModel' not found" -ForegroundColor Yellow
        Write-Host "   Update OLLAMA_MODEL in start_server.ps1 to one of the above" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ✗ Ollama API not responding" -ForegroundColor Red
    Write-Host "   Start Ollama in a new terminal: ollama serve" -ForegroundColor Yellow
    Write-Host "   Keep that terminal open!" -ForegroundColor Yellow
}

# 5. Check Python environment
Write-Host "`n5. Checking Python..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   ✓ $pythonVersion" -ForegroundColor Green
    
    # Check for uvicorn
    $uvicornCheck = python -c "import uvicorn; print(uvicorn.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ uvicorn $uvicornCheck" -ForegroundColor Green
    } else {
        Write-Host "   ✗ uvicorn not installed" -ForegroundColor Red
        Write-Host "   Install: pip install uvicorn" -ForegroundColor Yellow
    }
    
    # Check for fastapi
    $fastapiCheck = python -c "import fastapi; print(fastapi.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ fastapi $fastapiCheck" -ForegroundColor Green
    } else {
        Write-Host "   ✗ fastapi not installed" -ForegroundColor Red
        Write-Host "   Install: pip install fastapi" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ✗ Python not found" -ForegroundColor Red
}

# 6. Check for running Python processes
Write-Host "`n6. Checking for running Python processes..." -ForegroundColor Cyan
$pythonProcs = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcs) {
    Write-Host "   ⚠ Found $($pythonProcs.Count) Python process(es):" -ForegroundColor Yellow
    foreach ($proc in $pythonProcs) {
        Write-Host "     - PID $($proc.Id): $($proc.Path)" -ForegroundColor Gray
    }
    Write-Host "   To kill all: Get-Process python | Stop-Process -Force" -ForegroundColor Yellow
} else {
    Write-Host "   ✓ No Python processes running" -ForegroundColor Green
}

# 7. Environment variables check
Write-Host "`n7. Key environment variables:" -ForegroundColor Cyan
$envVars = @(
    "OLLAMA_BASE",
    "OLLAMA_MODEL",
    "DATABASE_URL",
    "ES_ENABLED",
    "SCHEDULER_ENABLED",
    "FEATURE_SUMMARIZE",
    "FEATURE_RAG_SEARCH"
)

foreach ($var in $envVars) {
    $value = [Environment]::GetEnvironmentVariable($var)
    if ($value) {
        Write-Host "   $var = $value" -ForegroundColor Gray
    }
}

Write-Host "`n=== Diagnostics Complete ===`n" -ForegroundColor Green

# Recommendations
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Fix any ✗ issues above" -ForegroundColor White
Write-Host "2. Run: .\start_in_new_window.ps1" -ForegroundColor White
Write-Host "3. Wait 10 seconds, then run: .\check_routes.ps1" -ForegroundColor White
Write-Host ""
