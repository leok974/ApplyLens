#!/usr/bin/env bash
# Sanity check script for dbt setup
# Verifies clean state and runs local builds

set -e

echo ""
echo "🔍 dbt Sanity Check"
echo "=================="
echo ""

# Check current directory
if [[ ! "$(basename $(pwd))" == "ApplyLens" ]]; then
    echo "⚠️  Run this script from the ApplyLens root directory"
    exit 1
fi

# 1. Verify dbt_packages is not tracked
echo "1️⃣  Checking git tracking..."
tracked_count=$(git ls-files analytics/dbt/dbt_packages/ | wc -l)
if [[ $tracked_count -gt 0 ]]; then
    echo "   ❌ dbt_packages/ is tracked in git ($tracked_count files)"
    echo "   Run: git rm -r --cached analytics/dbt/dbt_packages/"
    exit 1
else
    echo "   ✅ dbt_packages/ not tracked"
fi

# 2. Verify .gitignore exists and is complete
echo ""
echo "2️⃣  Checking .gitignore..."
patterns=(
    "analytics/dbt/dbt_packages/"
    "analytics/dbt/target/"
    "analytics/dbt/package-lock.yml"
)

for pattern in "${patterns[@]}"; do
    if grep -qF "$pattern" .gitignore; then
        echo "   ✅ $pattern"
    else
        echo "   ❌ Missing: $pattern"
        exit 1
    fi
done

# 3. Verify packages.yml has pinned versions
echo ""
echo "3️⃣  Checking packages.yml..."
if grep -q 'version:\s*\[' analytics/dbt/packages.yml; then
    echo "   ❌ Found version ranges (use exact versions)"
    exit 1
else
    echo "   ✅ Using pinned versions"
fi

# 4. Clean and reinstall deps
echo ""
echo "4️⃣  Cleaning dbt artifacts..."
cd analytics/dbt
rm -rf dbt_packages package-lock.yml target logs 2>/dev/null || true
echo "   ✅ Cleaned: dbt_packages, package-lock.yml, target, logs"

echo ""
echo "5️⃣  Installing dbt packages..."
if dbt deps --target prod > /dev/null 2>&1; then
    echo "   ✅ dbt deps successful"
else
    echo "   ❌ dbt deps failed"
    cd ../..
    exit 1
fi

# 5. Optional: Run dbt build
echo ""
read -p "6️⃣  Run dbt build? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "   Running dbt run..."
    if dbt run --target prod --select models/staging/fivetran models/marts/warehouse; then
        echo "   ✅ dbt run successful"
    else
        echo "   ❌ dbt run failed"
        cd ../..
        exit 1
    fi

    echo ""
    echo "   Running dbt test..."
    if dbt test --target prod --select models/staging/fivetran models/marts/warehouse; then
        echo "   ✅ dbt test successful"
    else
        echo "   ❌ dbt test failed"
        cd ../..
        exit 1
    fi
fi

cd ../..

echo ""
echo "✅ All checks passed!"
echo ""
echo "📋 Quick commands:"
echo "   Clean deps:  cd analytics/dbt && rm -rf dbt_packages package-lock.yml && dbt deps"
echo "   Local build: cd analytics/dbt && dbt run --target prod && dbt test --target prod"
echo "   CI trigger:  gh workflow run 'Warehouse Nightly'"
echo ""
