#!/usr/bin/env bash
set -euo pipefail

# Run all dbt models with production configuration
# Usage: ./run-all.sh

# Set defaults
export GCP_PROJECT="${GCP_PROJECT:-applylens-gmail-1759983601}"
export RAW_DATASET="${RAW_DATASET:-gmail}"
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:-$PWD/../../secrets/applylens-warehouse-key.json}"

echo "=================================================="
echo "  dbt Warehouse - Full Run"
echo "=================================================="
echo ""
echo "Configuration:"
echo "  GCP_PROJECT: $GCP_PROJECT"
echo "  RAW_DATASET: $RAW_DATASET"
echo "  CREDENTIALS: $GOOGLE_APPLICATION_CREDENTIALS"
echo ""

# Change to dbt directory
cd "$(dirname "$0")/../dbt"

echo "1. Installing dependencies..."
dbt deps --target prod

echo ""
echo "2. Running models..."
dbt run --target prod --vars "raw_dataset: $RAW_DATASET" --select +marts.warehouse.*

echo ""
echo "3. Running tests..."
dbt test --target prod --vars "raw_dataset: $RAW_DATASET" --select +marts.warehouse.*

echo ""
echo "=================================================="
echo "  ✅ Complete!"
echo "=================================================="
