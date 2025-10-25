#!/bin/bash
# Cloudflare Cache Rules Setup for ApplyLens
# Purpose: Bypass cache for HTML, cache assets forever

set -e

echo "🔧 ApplyLens Cloudflare Cache Rules Setup"
echo "=========================================="
echo ""

# Check required environment variables
if [ -z "$CF_API_TOKEN" ] || [ -z "$CF_ZONE_ID" ]; then
  echo "❌ Error: Missing required environment variables"
  echo ""
  echo "Please set:"
  echo "  export CF_API_TOKEN='your_cloudflare_api_token'"
  echo "  export CF_ZONE_ID='your_zone_id'"
  echo ""
  echo "To get your Zone ID:"
  echo "  1. Go to https://dash.cloudflare.com/"
  echo "  2. Select your domain (applylens.app)"
  echo "  3. Zone ID is shown in the right sidebar"
  echo ""
  echo "To create an API Token:"
  echo "  1. Go to https://dash.cloudflare.com/profile/api-tokens"
  echo "  2. Create Token → Custom Token"
  echo "  3. Permissions:"
  echo "     - Zone → Cache Rules → Edit"
  echo "     - Zone → Cache Purge → Purge"
  echo "  4. Zone Resources:"
  echo "     - Include → Specific zone → applylens.app"
  exit 1
fi

CF_API="https://api.cloudflare.com/client/v4"

echo "✅ Environment variables configured"
echo "   Zone ID: $CF_ZONE_ID"
echo ""

# Step 1: Find or create the cache rules ruleset
echo "📋 Step 1: Finding cache rules ruleset..."
RULESET_ID=$(curl -s -H "Authorization: Bearer $CF_API_TOKEN" \
  "$CF_API/zones/$CF_ZONE_ID/rulesets" \
  | jq -r '.result[] | select(.phase=="http_request_cache_settings") | .id' \
  | head -1)

if [ -z "$RULESET_ID" ] || [ "$RULESET_ID" == "null" ]; then
  echo "   → No cache rules ruleset found. Creating one..."
  RULESET_ID=$(curl -s -X POST "$CF_API/zones/$CF_ZONE_ID/rulesets" \
    -H "Authorization: Bearer $CF_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "Cache Rules",
      "phase": "http_request_cache_settings",
      "rules": []
    }' | jq -r '.result.id')

  if [ -z "$RULESET_ID" ] || [ "$RULESET_ID" == "null" ]; then
    echo "❌ Failed to create ruleset"
    exit 1
  fi
  echo "   ✅ Created ruleset: $RULESET_ID"
else
  echo "   ✅ Found existing ruleset: $RULESET_ID"
fi

echo ""

# Step 2: Update cache rules
echo "📝 Step 2: Updating cache rules..."

cat > /tmp/cache-rules.json <<'JSON'
{
  "name": "ApplyLens Cache Rules",
  "phase": "http_request_cache_settings",
  "rules": [
    {
      "description": "Bypass cache for HTML entry points (always fetch fresh asset hashes)",
      "action": "set_cache_settings",
      "expression": "(http.request.uri.path eq \"/\" or starts_with(http.request.uri.path, \"/web/\") or ends_with(http.request.uri.path, \"/index.html\"))",
      "action_parameters": {
        "cache": "bypass"
      },
      "enabled": true
    },
    {
      "description": "Immutable cache for hashed assets (1 year for js/css/fonts/images)",
      "action": "set_cache_settings",
      "expression": "(starts_with(http.request.uri.path, \"/assets/\") or ends_with(http.request.uri.path, \".js\") or ends_with(http.request.uri.path, \".css\") or ends_with(http.request.uri.path, \".woff2\") or ends_with(http.request.uri.path, \".woff\") or ends_with(http.request.uri.path, \".svg\") or ends_with(http.request.uri.path, \".png\") or ends_with(http.request.uri.path, \".jpg\") or ends_with(http.request.uri.path, \".jpeg\") or ends_with(http.request.uri.path, \".webp\"))",
      "action_parameters": {
        "cache": "eligible",
        "edge_ttl": {
          "mode": "override_origin",
          "default": 31536000
        },
        "browser_ttl": {
          "mode": "respect_origin"
        },
        "respect_strong_etags": true
      },
      "enabled": true
    }
  ]
}
JSON

RESULT=$(curl -s -X PUT "$CF_API/zones/$CF_ZONE_ID/rulesets/$RULESET_ID" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data @/tmp/cache-rules.json)

SUCCESS=$(echo "$RESULT" | jq -r '.success')

if [ "$SUCCESS" == "true" ]; then
  echo "   ✅ Cache rules updated successfully"
  echo ""
  echo "   Rules created:"
  echo "$RESULT" | jq -r '.result.rules[].description' | sed 's/^/     - /'
else
  echo "   ❌ Failed to update cache rules"
  echo "$RESULT" | jq -r '.errors'
  exit 1
fi

echo ""

# Step 3: Purge cache
echo "🗑️  Step 3: Purging Cloudflare cache..."
PURGE_RESULT=$(curl -s -X POST "$CF_API/zones/$CF_ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      "https://applylens.app/",
      "https://applylens.app/web/",
      "https://applylens.app/web/index.html",
      "https://applylens.app/index.html"
    ]
  }')

PURGE_SUCCESS=$(echo "$PURGE_RESULT" | jq -r '.success')

if [ "$PURGE_SUCCESS" == "true" ]; then
  echo "   ✅ Cache purged successfully"
else
  echo "   ⚠️  Cache purge failed (may need manual purge)"
  echo "$PURGE_RESULT" | jq -r '.errors'
fi

echo ""
echo "✅ Configuration complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Wait 30-60 seconds for Cloudflare to propagate changes"
echo "   2. Clear your browser cache (DevTools → Application → Clear Storage)"
echo "   3. Visit https://applylens.app/web/search"
echo "   4. Open Console and verify: '🔍 ApplyLens Web v0.4.10'"
echo "   5. Perform a search and check Network tab for /api/search requests"
echo ""
echo "📊 Verification commands:"
echo "   # Check HTML is bypassed:"
echo "   curl -sI https://applylens.app/web/ | grep -i 'cache-control\\|cf-cache-status'"
echo ""
echo "   # Check API returns JSON:"
echo "   curl -sI 'https://applylens.app/api/search?q=test&limit=1' | grep -i content-type"
echo ""

# Cleanup
rm -f /tmp/cache-rules.json
