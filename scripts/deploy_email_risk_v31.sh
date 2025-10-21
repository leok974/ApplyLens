#!/usr/bin/env bash
# deploy_email_risk_v31.sh - Deploy Email Risk Detection v3.1 + Generate Test Data
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
if ! curl -fsS -X PUT "$ES_URL/_ingest/pipeline/$PIPELINE_NAME" \
  -H 'Content-Type: application/json' \
  --data-binary @"$PIPELINE_FILE"; then
  echo "   ❌ ERROR: Failed to upload pipeline"
  exit 1
fi
echo ""
echo "   ✅ Pipeline uploaded successfully"

# 3. Generate test emails
echo ""
echo "3) Generating test emails..."
if command -v python3 &> /dev/null; then
  PYTHON=python3
elif command -v python &> /dev/null; then
  PYTHON=python
else
  echo "   ⚠️  Python not found, skipping test generation"
  PYTHON=""
fi

if [ -n "$PYTHON" ]; then
  export ES_URL
  $PYTHON scripts/generate_test_emails.py
  echo "   ✅ Test emails generated"
else
  echo "   ℹ️  Skipping test generation (Python not available)"
fi

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Test Emails Generated (in index: gmail_emails-999999):"
echo "  • tc1-brand-mismatch - Brand mention + non-canonical domain"
echo "  • tc2-replyto-mismatch - Reply-To points to different domain"
echo "  • tc3-spf-dmarc-fail - SPF/DKIM/DMARC failures"
echo "  • tc4-shortener-anchor-mismatch - URL shorteners + anchor text mismatch"
echo "  • tc5-risky-attachments - Executable/macro attachments"
echo "  • tc6-young-domain - Newly registered offbrand domain"
echo "  • tc7-ok-control - Clean corporate email (should NOT flag)"
echo ""
echo "New v3.1 Signals:"
echo "  • SPF/DKIM/DMARC authentication failures"
echo "  • URL shorteners & anchor mismatches"
echo "  • Risky attachments (exe, scripts, macros)"
echo "  • Reply-To domain mismatches"
echo "  • Domain age (requires enrichment job)"
echo ""
echo "Verification (in Kibana Discover):"
echo "  Index: gmail_emails-999999"
echo "  High risk: suspicion_score >= 40"
echo "  Reply-To mismatch: explanations : \"Reply-To domain differs*\""
echo "  Shorteners: explanations : \"Uses link shortener*\""
echo "  Attachments: explanations : \"Contains risky attachment*\""
echo "  Control: _id : \"tc7-ok-control\" (should NOT be suspicious)"
echo ""
echo "Optional: Seed domain enrichment for tc6:"
echo "  curl -X PUT \"$ES_URL/domain_enrich/_doc/new-hire-team-hr.com\" \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"domain\":\"new-hire-team-hr.com\",\"age_days\":7}'"
echo ""
echo "API Endpoints:"
echo "  GET  /emails/{id}/risk-advice - Get risk assessment"
echo "  POST /emails/{id}/risk-feedback - Submit user feedback"
echo ""
echo "Next Steps:"
echo "  1. Query test index in Kibana: gmail_emails-999999"
echo "  2. Set up domain enrichment worker (services/workers/domain_enrich.py)"
echo "  3. Monitor Prometheus metrics: email_risk_served_total, email_risk_feedback_total"
echo ""
