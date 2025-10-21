# Feature Flag Verification Script
# Checks that all Phase 4 feature flags are properly configured

Write-Host "🚀 Phase 4 Feature Flags - Verification" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

$allGood = $true

# Check files exist
Write-Host "📁 Checking files..." -ForegroundColor Yellow

$files = @(
    "apps\web\src\lib\flags.ts",
    "apps\web\src\pages\DemoAI.tsx",
    "apps\web\tests\ai-flags.spec.ts",
    "apps\web\.env.local",
    "apps\web\.env.docker",
    "apps\web\.env.production",
    "apps\web\.env.example",
    "PHASE_4_FEATURE_FLAGS.md",
    "PHASE_4_FEATURE_FLAGS_SUMMARY.md"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file - MISSING" -ForegroundColor Red
        $allGood = $false
    }
}

# Check flags.ts content
Write-Host "`n🔍 Checking flags.ts implementation..." -ForegroundColor Yellow

$flagsContent = Get-Content "apps\web\src\lib\flags.ts" -Raw

$expectedFlags = @(
    "SUMMARIZE",
    "RISK_BADGE",
    "RAG_SEARCH",
    "DEMO_MODE"
)

foreach ($flag in $expectedFlags) {
    if ($flagsContent -match $flag) {
        Write-Host "  ✓ FLAG: $flag" -ForegroundColor Green
    } else {
        Write-Host "  ✗ FLAG: $flag - MISSING" -ForegroundColor Red
        $allGood = $false
    }
}

# Check helper functions
$helpers = @("hasAnyAIFeatures", "getEnabledFeatures")
foreach ($helper in $helpers) {
    if ($flagsContent -match $helper) {
        Write-Host "  ✓ Helper: $helper" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Helper: $helper - MISSING" -ForegroundColor Red
        $allGood = $false
    }
}

# Check .env files have flag definitions
Write-Host "`n⚙️  Checking environment files..." -ForegroundColor Yellow

$envFiles = @(
    @{ Path = "apps\web\.env.local"; Name = "Development" },
    @{ Path = "apps\web\.env.docker"; Name = "Docker" },
    @{ Path = "apps\web\.env.production"; Name = "Production" }
)

foreach ($env in $envFiles) {
    $content = Get-Content $env.Path -Raw
    Write-Host "  $($env.Name) ($($env.Path)):" -ForegroundColor Cyan
    
    foreach ($flag in @("VITE_FEATURE_SUMMARIZE", "VITE_FEATURE_RISK_BADGE", "VITE_FEATURE_RAG_SEARCH", "VITE_DEMO_MODE")) {
        if ($content -match $flag) {
            $value = if ($content -match "$flag=1") { "ENABLED" } else { "DISABLED" }
            $color = if ($value -eq "ENABLED") { "Green" } else { "Gray" }
            Write-Host "    ✓ $flag = $value" -ForegroundColor $color
        } else {
            Write-Host "    ✗ $flag - MISSING" -ForegroundColor Red
            $allGood = $false
        }
    }
}

# Check DemoAI.tsx uses FLAGS
Write-Host "`n🎨 Checking DemoAI.tsx integration..." -ForegroundColor Yellow

$demoContent = Get-Content "apps\web\src\pages\DemoAI.tsx" -Raw

if ($demoContent -match "import.*FLAGS.*from.*@/lib/flags") {
    Write-Host "  ✓ FLAGS imported" -ForegroundColor Green
} else {
    Write-Host "  ✗ FLAGS not imported" -ForegroundColor Red
    $allGood = $false
}

$conditionals = @(
    "FLAGS.SUMMARIZE",
    "FLAGS.RISK_BADGE",
    "FLAGS.RAG_SEARCH",
    "FLAGS.DEMO_MODE"
)

foreach ($cond in $conditionals) {
    if ($demoContent -match $cond) {
        Write-Host "  ✓ Uses $cond" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Missing $cond" -ForegroundColor Red
        $allGood = $false
    }
}

# Check test file
Write-Host "`n🧪 Checking Playwright tests..." -ForegroundColor Yellow

$testContent = Get-Content "apps\web\tests\ai-flags.spec.ts" -Raw

$testCases = @(
    "all features visible when flags are enabled",
    "components hidden when flags are disabled",
    "only summarize feature enabled",
    "only risk badge enabled",
    "only RAG search enabled"
)

foreach ($test in $testCases) {
    if ($testContent -match $test) {
        Write-Host "  ✓ Test: $test" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Test: $test - MISSING" -ForegroundColor Yellow
    }
}

# Summary
Write-Host "`n" + "="*50 -ForegroundColor Cyan

if ($allGood) {
    Write-Host "✅ All feature flag checks passed!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "  1. Restart web dev server: cd apps\web && npm run dev"
    Write-Host "  2. Navigate to: http://localhost:5173/demo-ai"
    Write-Host "  3. Run tests: npx playwright test ai-flags.spec.ts"
    Write-Host "  4. Integrate flags into existing email views"
} else {
    Write-Host "❌ Some checks failed - please review above" -ForegroundColor Red
    exit 1
}

Write-Host "`n📚 Documentation:" -ForegroundColor Cyan
Write-Host "  - PHASE_4_FEATURE_FLAGS.md (comprehensive guide)"
Write-Host "  - PHASE_4_FEATURE_FLAGS_SUMMARY.md (quick reference)"
Write-Host "  - PHASE_4_FRONTEND_INTEGRATION.md (component integration)"
