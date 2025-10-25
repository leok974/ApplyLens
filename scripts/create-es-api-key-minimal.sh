#!/bin/bash
# Create a least-privilege Elasticsearch API key for ApplyLens
# This version uses minimal permissions - safer for production

set -e

# Check prerequisites
if [ -z "$ES_ENDPOINT" ]; then
    echo "Error: ES_ENDPOINT is not set"
    exit 1
fi

if [ -z "$ES_USER" ]; then
    echo "Error: ES_USER is not set"
    exit 1
fi

if [ -z "$ES_PASS" ]; then
    echo "Error: ES_PASS is not set"
    exit 1
fi

echo "Creating Least-Privilege Elasticsearch API key for ApplyLens..."
echo "Endpoint: $ES_ENDPOINT"
echo ""

# Create least-privilege API key
RESPONSE=$(curl -sS -u "$ES_USER:$ES_PASS" \
    -H "Content-Type: application/json" \
    -X POST "$ES_ENDPOINT/_security/api_key" \
    -d '{
        "name": "applylens-api-minimal",
        "role_descriptors": {
          "applylens_minimal": {
            "cluster": [
              "monitor",
              "manage_index_templates",
              "manage_ilm",
              "manage_ingest_pipelines"
            ],
            "index": [{
              "names": ["gmail_emails-*","applylens-*",".applylens-*"],
              "privileges": [
                "read",
                "write",
                "index",
                "create",
                "create_index",
                "view_index_metadata"
              ]
            }]
          }
        }
      }')

# Check if response contains an error
if echo "$RESPONSE" | grep -q '"error"'; then
    echo "Error creating API key:"
    echo "$RESPONSE" | jq '.'
    exit 1
fi

# Pretty print the response
echo "✓ Least-Privilege API Key created successfully!"
echo ""
echo "$RESPONSE" | jq '.'
echo ""

# Extract the encoded key
ENCODED=$(echo "$RESPONSE" | jq -r '.encoded')
API_KEY_ID=$(echo "$RESPONSE" | jq -r '.id')

if [ "$ENCODED" = "null" ] || [ -z "$ENCODED" ]; then
    echo "Error: Could not extract encoded API key from response"
    exit 1
fi

echo "=========================================="
echo "Least-Privilege API Key Details:"
echo "=========================================="
echo "ID:      $API_KEY_ID"
echo "Name:    applylens-api-minimal"
echo "Encoded: $ENCODED"
echo ""
echo "Cluster Permissions:"
echo "  ✓ monitor                    (health, stats)"
echo "  ✓ manage_index_templates     (templates)"
echo "  ✓ manage_ilm                 (lifecycle)"
echo "  ✓ manage_ingest_pipelines    (pipelines)"
echo ""
echo "Index Permissions (gmail_emails-*, applylens-*, .applylens-*):"
echo "  ✓ read                       (query/search)"
echo "  ✓ write                      (update docs)"
echo "  ✓ index                      (index docs)"
echo "  ✓ create                     (create docs)"
echo "  ✓ create_index               (create indices)"
echo "  ✓ view_index_metadata        (view mappings)"
echo ""
echo "Security Restrictions:"
echo "  ✗ Cannot manage index settings"
echo "  ✗ Cannot delete documents"
echo "  ✗ Cannot delete indices"
echo "  ✗ Cannot manage aliases"
echo "  ✗ No cluster admin operations"
echo "=========================================="
echo ""

# Update .env file
echo "Updating ELASTICSEARCH_API_KEY in .env file..."
if [ -f .env ]; then
    # Remove existing ELASTICSEARCH_API_KEY if present
    sed -i.bak '/^ELASTICSEARCH_API_KEY=/d' .env
fi
echo "ELASTICSEARCH_API_KEY=$ENCODED" >> .env
echo "✓ Updated .env file"
echo ""

# Verify the key works
echo "Verifying least-privilege API key..."
HEALTH=$(curl -sS -H "Authorization: ApiKey $ENCODED" "$ES_ENDPOINT/_cluster/health")

if echo "$HEALTH" | grep -q '"status"'; then
    echo "✓ Cluster health check: PASSED"
    STATUS=$(echo "$HEALTH" | jq -r '.status')
    echo "  Status: $STATUS"
else
    echo "⚠ Cluster health check failed"
    exit 1
fi

# Test write permission
echo ""
echo "Testing write permissions..."
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
WRITE_RESULT=$(curl -sS -H "Authorization: ApiKey $ENCODED" \
    -H "Content-Type: application/json" \
    -X POST "$ES_ENDPOINT/applylens-test/_doc/test-$(date +%s)" \
    -d "{\"test\":\"least_privilege_verification\",\"timestamp\":\"$TIMESTAMP\"}" 2>&1)

if echo "$WRITE_RESULT" | grep -q '"result"'; then
    echo "✓ Write test: PASSED (can index documents)"
else
    echo "⚠ Write test failed (may be expected if index pattern doesn't match)"
fi

# Test delete restriction
echo ""
echo "Testing security restrictions..."
DELETE_RESULT=$(curl -sS -w "%{http_code}" -o /dev/null \
    -H "Authorization: ApiKey $ENCODED" \
    -X DELETE "$ES_ENDPOINT/applylens-test" 2>&1)

if [ "$DELETE_RESULT" = "403" ] || [ "$DELETE_RESULT" = "405" ]; then
    echo "✓ Delete index: BLOCKED (403/405 - correct!)"
elif [ "$DELETE_RESULT" = "200" ]; then
    echo "⚠ WARNING: Delete index succeeded - key has too many privileges!"
else
    echo "? Delete test returned: $DELETE_RESULT"
fi

echo ""
echo "=========================================="
echo "Least-Privilege Setup Complete!"
echo "=========================================="
echo ""
echo "Advantages over 'all' privilege:"
echo "  ✓ Cannot accidentally delete indices"
echo "  ✓ Cannot modify index settings in production"
echo "  ✓ Limited to read/write operations only"
echo "  ✓ Follows principle of least privilege"
echo "  ✓ Safer for production environments"
echo ""
echo "To revoke old enhanced key:"
echo "  curl -sS -u \"\$ES_USER:\$ES_PASS\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -X DELETE \"\$ES_ENDPOINT/_security/api_key\" \\"
echo "    -d '{\"ids\": [\"uVibDZoBZNl7zqftzkFo\"]}' | jq"
