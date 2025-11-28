# launch-applylens-workday.ps1
param(
  [ValidateSet('local','prod')]
  [string]$Env = 'local',
  [int]$SeedCount = 40
)

function Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "[OK]   $msg" -ForegroundColor Green }
function Err($msg)  { Write-Host "[ERR]  $msg" -ForegroundColor Red }

$InfraWorkspace = "D:\ApplyLens Infra Ops.code-workspace"
$DevWorkspace   = "D:\ApplyLens Dev.code-workspace"

if (-not (Test-Path $InfraWorkspace)) {
  Err "Infra workspace not found at $InfraWorkspace. Update the path or move the file."
}
if (-not (Test-Path $DevWorkspace)) {
  Err "Dev workspace not found at $DevWorkspace. Update the path or move the file."
}

if ($Env -eq 'local') {
  $BaseApi = "http://127.0.0.1:8003"
  $BaseUi  = "http://127.0.0.1:5175"
  $ComposeDir = "D:\ApplyLens\infra"
  $ComposeFile = "docker-compose.yml"
} else {
  $BaseApi = "https://applylens.app/api"
  $BaseUi  = "https://applylens.app"
  $ComposeDir = "D:\ApplyLens\infra"
  $ComposeFile = "docker-compose.prod.yml"
}

Info "Starting containers ($Env)…"
Push-Location $ComposeDir
try {
  docker compose -f $ComposeFile pull | Write-Output
  docker compose -f $ComposeFile up -d | Write-Output
  Ok "Containers started."
} finally {
  Pop-Location
}

Info "Opening workspaces…"
Start-Process code "`"$InfraWorkspace`""
Start-Process code "`"$DevWorkspace`""

Info "Seeding inbox (count=$SeedCount)…"
$env:E2E_BASE_URL = $BaseApi -replace "/api$", ""  # base origin w/o /api
$env:E2E_API = $BaseApi
$env:SEED_COUNT = "$SeedCount"

# Optional: run Playwright smoke if available
$RepoRoot = "D:\ApplyLens"
if (Test-Path "$RepoRoot\package.json") {
  Push-Location $RepoRoot
  try {
    if (Test-Path ".\node_modules\.bin\playwright.cmd") {
      .\node_modules\.bin\playwright.cmd test apps/web/tests/smoke/inbox-has-data.spec.ts --config=playwright.config.ts
    } else {
      if (Get-Command "npx" -ErrorAction SilentlyContinue) {
        npx playwright test apps/web/tests/smoke/inbox-has-data.spec.ts --config=playwright.config.ts
      } else {
        Info "Playwright not installed. Skipping smoke."
      }
    }
  } finally {
    Pop-Location
  }
} else {
  Info "Repo root not found at $RepoRoot; skipping smoke."
}

Ok "All set. UI: $BaseUi  API: $BaseApi"
