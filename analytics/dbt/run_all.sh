#!/usr/bin/env bash
# dbt Run All - Bash
# Usage: ./analytics/dbt/run_all.sh
#
# Runs full dbt pipeline: deps → seed → run → test
# Sets working directory to analytics/dbt automatically

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SKIP_TESTS=false
FULL_REFRESH=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --full-refresh)
            FULL_REFRESH=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "dbt Run All - ApplyLens Analytics"
echo "Working directory: $SCRIPT_DIR"
echo "========================================"
echo ""

# Step 1: Install dependencies
echo "[1/4] Installing dbt dependencies..."
dbt deps
echo "✓ Dependencies installed"
echo ""

# Step 2: Load seed data
echo "[2/4] Loading seed data..."
if [ "$FULL_REFRESH" = true ]; then
    dbt seed --full-refresh
else
    dbt seed
fi
echo "✓ Seeds loaded"
echo ""

# Step 3: Run models
echo "[3/4] Running dbt models..."
if [ "$FULL_REFRESH" = true ]; then
    dbt run --full-refresh
else
    dbt run
fi
echo "✓ Models built"
echo ""

# Step 4: Run tests (unless skipped)
if [ "$SKIP_TESTS" = false ]; then
    echo "[4/4] Running dbt tests..."
    if dbt test; then
        echo "✓ All tests passed"
    else
        echo "⚠ Some tests failed (non-blocking)"
    fi
    echo ""
else
    echo "[4/4] Skipping tests (--skip-tests flag)"
    echo ""
fi

echo "========================================"
echo "dbt pipeline complete!"
echo "========================================"
