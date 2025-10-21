#!/usr/bin/env bash
# CI/CD Pre-deployment Validation Script
# Ensures critical environment variables are set before deployment

set -euo pipefail

echo "========================================="
echo "🔍 Pre-Deployment Validation"
echo "========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# Function to check environment variable
check_env_var() {
    local var_name=$1
    local required=${2:-true}
    local masked=${3:-false}
    
    if [ -n "${!var_name:-}" ]; then
        if [ "$masked" = true ]; then
            echo -e "${GREEN}✓${NC} $var_name: [MASKED]"
        else
            echo -e "${GREEN}✓${NC} $var_name: ${!var_name}"
        fi
    else
        if [ "$required" = true ]; then
            echo -e "${RED}✗${NC} $var_name: MISSING (required)"
            ERRORS=$((ERRORS + 1))
        else
            echo -e "${YELLOW}⚠${NC} $var_name: not set (optional)"
        fi
    fi
}

echo "🔐 Security Configuration"
echo "-------------------------"
check_env_var "APPLYLENS_AES_KEY_BASE64" true true
check_env_var "CSRF_SECRET_KEY" true true
check_env_var "OAUTH_STATE_SECRET" true true
check_env_var "HMAC_SECRET" false true  # Optional - used by Kibana, in infra/.env

echo ""
echo "🗄️  Database Configuration"
echo "-------------------------"
check_env_var "DATABASE_URL" true false
check_env_var "POSTGRES_PASSWORD" true true

echo ""
echo "🔍 Search & Analytics"
echo "-------------------------"
check_env_var "ES_URL" true false
check_env_var "ES_ENABLED" true false

echo ""
echo "🔑 OAuth Configuration"
echo "-------------------------"
check_env_var "GOOGLE_CLIENT_ID" true false
check_env_var "GOOGLE_CLIENT_SECRET" true true
check_env_var "GOOGLE_REDIRECT_URI" true false

echo ""
echo "📊 Monitoring (Optional)"
echo "-------------------------"
check_env_var "PROMETHEUS_ENABLED" false false
check_env_var "RECAPTCHA_ENABLED" false false

echo ""
echo "========================================="

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ Validation Failed: $ERRORS error(s) found${NC}"
    echo ""
    echo "💡 Fix required:"
    echo "   - Ensure all required environment variables are set"
    echo "   - Check .env file or CI/CD secrets configuration"
    echo "   - For AES key: run 'python scripts/generate_aes_key.py'"
    echo ""
    exit 1
else
    echo -e "${GREEN}✅ All validation checks passed!${NC}"
    echo ""
    echo "🚀 Ready for deployment"
    echo ""
    exit 0
fi
