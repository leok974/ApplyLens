#!/usr/bin/env bash
# deploy_email_risk_v31.sh - Deploy Email Risk Detection v3.1
# Multi-signal phishing detection: SPF/DKIM/DMARC, URL inspection, attachments, reply-to, domain age

set -euo pipefail

ES_URL="${ES_URL:-http://localhost:9200}"
PIPELINE_NAME="applylens_emails_v3"
PIPELINE_FILE="infra/elasticsearch/pipelines/emails_v3.json"

echo "=========================================="
echo "Email Risk Detection v3.1 Deployment"
echo "=========================================="
echo "Elasticsearch: $ES_URL"
echo "Pipeline: $PIPELINE_NAME"
echo ""

# 1. Check Elasticsearch connectivity
echo "1) Checking Elasticsearch connectivity..."
if ! curl -sf "$ES_URL" > /dev/null; then
  echo "   ❌ ERROR: Cannot connect to Elasticsearch at $ES_URL"
  exit 1
fi
echo "   ✅ Connected to Elasticsearch"

# 2. Upload pipeline
echo ""
echo "2) Uploading pipeline $PIPELINE_NAME..."
if ! curl -sf -X PUT "$ES_URL/_ingest/pipeline/$PIPELINE_NAME" \
  -H 'Content-Type: application/json' \
  --data-binary @"$PIPELINE_FILE"; then
  echo "   ❌ ERROR: Failed to upload pipeline"
  exit 1
fi
echo ""
echo "   ✅ Pipeline uploaded successfully"

# 3. Verify pipeline
echo ""
echo "3) Verifying pipeline..."
if ! curl -sf "$ES_URL/_ingest/pipeline/$PIPELINE_NAME" | jq '.'; then
  echo "   ❌ ERROR: Pipeline verification failed"
  exit 1
fi
echo "   ✅ Pipeline verified"

# 4. Optional: Create domain enrichment index
echo ""
echo "4) Creating domain_enrich index (optional)..."
curl -sf -X PUT "$ES_URL/domain_enrich" -H 'Content-Type: application/json' -d '{
  "mappings": {
    "properties": {
      "domain": { "type": "keyword" },
      "created_at": { "type": "date" },
      "mx_host": { "type": "keyword" },
      "age_days": { "type": "integer" },
      "risk_hint": { "type": "keyword" }
    }
  }
}' || echo "   ℹ️  Index may already exist"

# 5. Test with sample scam email
echo ""
echo "5) Testing with sample scam email..."
SAMPLE_ID="test_scam_v31_$(date +%s)"
curl -sf -X PUT "$ES_URL/gmail_emails/_doc/$SAMPLE_ID?pipeline=$PIPELINE_NAME" \
  -H 'Content-Type: application/json' -d '{
  "from": "hr.recruitment@suspicious-domain.info",
  "reply_to": "payments@totally-different.biz",
  "subject": "Urgent: Prometric Interview Opportunity",
  "body_text": "Congratulations! You have been selected. Equipment will be provided. Reply with your SSN and bank details. http://bit.ly/fake123",
  "body_html": "<a href=\"http://malicious.com\">Click here for Prometric portal</a>",
  "headers_received_spf": "Received-SPF: fail",
  "headers_authentication_results": "dkim=fail; dmarc=fail",
  "attachments": [
    { "filename": "instructions.exe", "mime": "application/octet-stream" }
  ],
  "received_at": "2025-10-21T10:00:00Z"
}' > /dev/null
echo "   ✅ Sample email ingested"

# 6. Validate signals detected
echo ""
echo "6) Validating signal detection..."
RESULT=$(curl -sf "$ES_URL/gmail_emails/_doc/$SAMPLE_ID" | jq '._source')
SCORE=$(echo "$RESULT" | jq -r '.suspicion_score // 0')
SUSPICIOUS=$(echo "$RESULT" | jq -r '.suspicious // false')
SIGNALS=$(echo "$RESULT" | jq -r '.explanations | length')

echo "   Suspicion Score: $SCORE"
echo "   Suspicious: $SUSPICIOUS"
echo "   Signals Detected: $SIGNALS"

if [ "$SUSPICIOUS" = "true" ] && [ "$SCORE" -gt 40 ]; then
  echo "   ✅ Multi-signal detection working"
else
  echo "   ⚠️  Warning: Expected suspicious=true with high score"
fi

# 7. Cleanup test email
echo ""
echo "7) Cleaning up test email..."
curl -sf -X DELETE "$ES_URL/gmail_emails/_doc/$SAMPLE_ID" > /dev/null
echo "   ✅ Test email deleted"

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "New v3.1 Signals:"
echo "  • SPF/DKIM/DMARC authentication failures"
echo "  • URL shorteners & anchor mismatches"
echo "  • Risky attachments (exe, scripts, macros)"
echo "  • Reply-To domain mismatches"
echo "  • Domain age (requires enrichment job)"
echo ""
echo "API Endpoints:"
echo "  GET  /emails/{id}/risk-advice - Get risk assessment"
echo "  POST /emails/{id}/risk-feedback - Submit user feedback"
echo ""
echo "Prometheus Metrics:"
echo "  applylens_email_risk_served_total{level}"
echo "  applylens_email_risk_feedback_total{verdict}"
echo ""
echo "Next Steps:"
echo "  1. Ensure Gmail API indexes header fields (Authentication-Results, Received-SPF, Reply-To)"
echo "  2. Set up domain enrichment worker (services/workers/domain_enrich.py)"
echo "  3. Test with real emails via /emails/{id}/risk-advice"
echo "  4. Monitor Prometheus metrics and user feedback"
echo ""
