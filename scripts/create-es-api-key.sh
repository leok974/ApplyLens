#!/bin/bash
# Create an Elasticsearch API key for ApplyLens via the cluster REST API
#
# Prerequisites:
#   - Set ES_ENDPOINT to your cluster endpoint, e.g.
#       export ES_ENDPOINT="https://YOUR-DEPLOYMENT.es.us-east-1.aws.elastic-cloud.com:9243"
#   - Set ES_USER and ES_PASS to your elastic credentials or a limited user
#   - Requires 'manage_api_key' cluster privilege
#
# Usage:
#   ./scripts/create-es-api-key.sh

set -e

# Check prerequisites
if [ -z "$ES_ENDPOINT" ]; then
    echo "Error: ES_ENDPOINT is not set"
    echo "Example: export ES_ENDPOINT='https://YOUR-DEPLOYMENT.es.us-east-1.aws.elastic-cloud.com:9243'"
    exit 1
fi

if [ -z "$ES_USER" ]; then
    echo "Error: ES_USER is not set"
    echo "Example: export ES_USER='elastic'"
    exit 1
fi

if [ -z "$ES_PASS" ]; then
    echo "Error: ES_PASS is not set"
    echo "Example: export ES_PASS='your-password'"
    exit 1
fi

echo "Creating Elasticsearch API key for ApplyLens..."
echo "Endpoint: $ES_ENDPOINT"
echo ""

# Create API key with limited privileges
RESPONSE=$(curl -s -X POST "$ES_ENDPOINT/_security/api_key" \
    -u "$ES_USER:$ES_PASS" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "applylens-api",
      "role_descriptors": {
        "applylens_writer": {
          "cluster": ["monitor"],
          "index": [{
            "names": ["gmail_emails-*"],
            "privileges": ["read", "write", "create", "create_index", "manage"]
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
echo "API Key created successfully:"
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
echo "API Key Details:"
echo "=========================================="
echo "ID:      $API_KEY_ID"
echo "Encoded: $ENCODED"
echo ""

# Append to .env file
echo "Adding ELASTICSEARCH_API_KEY to .env file..."
if [ -f .env ]; then
    # Remove existing ELASTICSEARCH_API_KEY if present
    sed -i '/^ELASTICSEARCH_API_KEY=/d' .env
fi
echo "ELASTICSEARCH_API_KEY=$ENCODED" >> .env
echo "✓ Added to .env file"
echo ""

# Verify the key works
echo "Verifying API key..."
HEALTH=$(curl -s -H "Authorization: ApiKey $ENCODED" "$ES_ENDPOINT/_cluster/health?pretty")

if echo "$HEALTH" | grep -q '"status"'; then
    echo "✓ API Key verification successful!"
    echo ""
    echo "Cluster Health:"
    echo "$HEALTH"
else
    echo "⚠ API Key verification failed:"
    echo "$HEALTH"
    exit 1
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo "The ELASTICSEARCH_API_KEY has been added to .env"
echo ""
echo "To use in docker-compose.prod.yml, add:"
echo "  environment:"
echo "    - ELASTICSEARCH_API_KEY=\${ELASTICSEARCH_API_KEY}"
echo ""
echo "To revoke this key later:"
echo "  curl -X DELETE '$ES_ENDPOINT/_security/api_key' \\"
echo "    -u '\$ES_USER:\$ES_PASS' \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"ids\": [\"$API_KEY_ID\"]}'"
