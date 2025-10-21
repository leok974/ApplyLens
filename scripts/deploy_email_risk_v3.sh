#!/usr/bin/env bash
# Quick deployment script for Email Risk Detection v3
set -euo pipefail

ES_URL="${ES_URL:-http://localhost:9200}"
PIPELINE_FILE="infra/elasticsearch/pipelines/emails_v3.json"

echo "🚀 Deploying Email Risk Detection v3 to Elasticsearch"
echo "   ES_URL: $ES_URL"
echo ""

# 1. Upload pipeline
echo "→ Uploading ingest pipeline applylens_emails_v3..."
if ! curl -fsS -X PUT "${ES_URL}/_ingest/pipeline/applylens_emails_v3" \
  -H 'Content-Type: application/json' \
  --data-binary "@${PIPELINE_FILE}"; then
  echo "✗ Failed to upload pipeline"
  exit 1
fi
echo "✓ Pipeline uploaded"
echo ""

# 2. Verify pipeline
echo "→ Verifying pipeline exists..."
if curl -fsS "${ES_URL}/_ingest/pipeline/applylens_emails_v3" > /dev/null; then
  echo "✓ Pipeline verified"
else
  echo "✗ Pipeline verification failed"
  exit 1
fi
echo ""

# 3. Test with sample scam email
echo "→ Testing with sample scam email..."
TEST_DOC='{
  "subject": "Job Opportunity - Remote Work",
  "from": "recruiter@shady-jobs.com",
  "body_text": "Hi! Prometric is hiring. Equipment will be provided. Reply with your name, phone, and location. Screening test will be emailed. Flexible hours, work from anywhere!",
  "received_at": "2025-10-21T10:00:00Z"
}'

RESPONSE=$(curl -fsS -X POST "${ES_URL}/gmail_emails/_doc?pipeline=applylens_emails_v3&refresh=true" \
  -H 'Content-Type: application/json' \
  -d "$TEST_DOC")

DOC_ID=$(echo "$RESPONSE" | jq -r '._id')
echo "✓ Test document indexed: $DOC_ID"
echo ""

# 4. Retrieve and check suspicion score
echo "→ Checking suspicion score..."
DOC_RESULT=$(curl -fsS "${ES_URL}/gmail_emails/_doc/${DOC_ID}?_source=suspicious,suspicion_score,explanations")

SUSPICIOUS=$(echo "$DOC_RESULT" | jq -r '._source.suspicious')
SCORE=$(echo "$DOC_RESULT" | jq -r '._source.suspicion_score')
EXPLANATIONS=$(echo "$DOC_RESULT" | jq -r '._source.explanations[]')

if [ "$SUSPICIOUS" = "true" ]; then
  echo "✓ Email correctly flagged as suspicious"
  echo "  Score: $SCORE"
  echo "  Reasons:"
  echo "$EXPLANATIONS" | sed 's/^/    - /'
  echo ""
  echo "✅ Deployment successful!"
else
  echo "⚠ Warning: Test email not flagged as suspicious (score: $SCORE)"
  echo "  This might indicate pipeline configuration needs adjustment"
fi
echo ""

# 5. Clean up test document
echo "→ Cleaning up test document..."
curl -fsS -X DELETE "${ES_URL}/gmail_emails/_doc/${DOC_ID}" > /dev/null
echo "✓ Test document deleted"
echo ""

echo "=========================================="
echo "Next steps:"
echo "1. Update index template to use v3 pipeline (optional)"
echo "2. Reindex existing emails for backfill"
echo "3. Restart API to pick up new /emails/{id}/risk-advice route"
echo "4. Deploy updated frontend"
echo ""
echo "See docs/EMAIL_RISK_DETECTION_V3.md for detailed instructions"
