#!/bin/bash
# Setup GitHub Actions Secrets for Warehouse Integration
# Run this script once to configure all required secrets

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  GitHub Actions Secrets Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo "Install: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}Not authenticated to GitHub. Running login...${NC}"
    gh auth login
fi

# Set repository (auto-detect or manual)
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
if [ -z "$REPO" ]; then
    echo -e "${YELLOW}Could not auto-detect repository.${NC}"
    read -p "Enter repository (owner/repo): " REPO
fi

echo -e "${GREEN}Setting secrets for: $REPO${NC}"
echo ""

# 1. GCP_PROJECT
echo -e "${YELLOW}1. GCP_PROJECT${NC}"
GCP_PROJECT="applylens-gmail-1759983601"
echo "   Value: $GCP_PROJECT"
gh secret set GCP_PROJECT --body "$GCP_PROJECT" --repo "$REPO"
echo -e "${GREEN}   ✓ Set${NC}"
echo ""

# 2. GCP_SA_JSON
echo -e "${YELLOW}2. GCP_SA_JSON (Service Account Key)${NC}"
SA_KEY_PATH="./secrets/applylens-warehouse-key.json"
if [ ! -f "$SA_KEY_PATH" ]; then
    echo -e "${RED}   Error: $SA_KEY_PATH not found${NC}"
    exit 1
fi
echo "   Reading from: $SA_KEY_PATH"
gh secret set GCP_SA_JSON --body "$(cat $SA_KEY_PATH)" --repo "$REPO"
echo -e "${GREEN}   ✓ Set ($(wc -c < $SA_KEY_PATH) bytes)${NC}"
echo ""

# 3. ES_URL
echo -e "${YELLOW}3. ES_URL (Elasticsearch URL)${NC}"
read -p "   Enter ES_URL (default: http://elasticsearch:9200): " ES_URL
ES_URL=${ES_URL:-http://elasticsearch:9200}
echo "   Value: $ES_URL"
gh secret set ES_URL --body "$ES_URL" --repo "$REPO"
echo -e "${GREEN}   ✓ Set${NC}"
echo ""

# 4. PUSHGATEWAY_URL
echo -e "${YELLOW}4. PUSHGATEWAY_URL (Prometheus Pushgateway)${NC}"
read -p "   Enter PUSHGATEWAY_URL (default: http://prometheus-pushgateway:9091): " PUSHGATEWAY_URL
PUSHGATEWAY_URL=${PUSHGATEWAY_URL:-http://prometheus-pushgateway:9091}
echo "   Value: $PUSHGATEWAY_URL"
gh secret set PUSHGATEWAY_URL --body "$PUSHGATEWAY_URL" --repo "$REPO"
echo -e "${GREEN}   ✓ Set${NC}"
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Secrets configured:"
echo "  ✓ GCP_PROJECT"
echo "  ✓ GCP_SA_JSON"
echo "  ✓ ES_URL"
echo "  ✓ PUSHGATEWAY_URL"
echo ""
echo "Next steps:"
echo "  1. Enable workflow: .github/workflows/dbt.yml"
echo "  2. Trigger manually: gh workflow run dbt.yml"
echo "  3. View runs: gh run list --workflow=dbt.yml"
echo ""
echo "Verify secrets:"
echo "  gh secret list --repo $REPO"
echo ""
