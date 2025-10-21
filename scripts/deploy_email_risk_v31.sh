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

# 4. Set up domain enrichment (optional but recommended)
echo ""
echo "4) Setting up domain enrichment..."
echo "   Creating enrich policy for domain age detection..."

ENRICH_POLICY='{
  "match": {
    "indices": "domain_enrich",
    "match_field": "domain",
    "enrich_fields": ["age_days", "risk_hint", "registrar", "mx_host"]
  }
}'

if curl -fsS -X PUT "$ES_URL/_enrich/policy/domain_age_policy" \
  -H 'Content-Type: application/json' \
  -d "$ENRICH_POLICY" > /dev/null; then
  echo "   ✅ Enrich policy created"

  # Execute policy (will fail if index doesn't exist yet, that's OK)
  if curl -fsS -X POST "$ES_URL/_enrich/policy/domain_age_policy/_execute" > /dev/null 2>&1; then
    echo "   ✅ Enrich policy executed"
  else
    echo "   ℹ️  Enrich policy execution skipped (run after enriching domains)"
  fi
else
  echo "   ℹ️  Enrich policy already exists or could not be created"
fi

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Test Emails Generated (in index: gmail_emails-999999):"
echo "  • tc1-brand-mismatch - Brand mention + non-canonical domain (105+ pts)"
echo "  • tc2-replyto-mismatch - Reply-To points to different domain (15+ pts)"
echo "  • tc3-spf-dmarc-fail - SPF/DKIM/DMARC failures (40+ pts)"
echo "  • tc4-shortener-anchor-mismatch - URL shorteners + anchor mismatch (30+ pts)"
echo "  • tc5-risky-attachments - Executable/macro attachments (20+ pts)"
echo "  • tc6-young-domain - Newly registered offbrand domain (15+ pts with enrichment)"
echo "  • tc7-ok-control - Clean corporate email (0 pts, NOT suspicious)"
echo ""
echo "New v3.1 Signals:"
echo "  • SPF/DKIM/DMARC authentication failures (+40 pts)"
echo "  • URL shorteners & anchor mismatches (+20 pts)"
echo "  • Risky attachments (exe, scripts, macros) (+20 pts)"
echo "  • Reply-To domain mismatches (+15 pts)"
echo "  • Domain age <30 days (+15 pts, requires enrichment)"
echo ""
echo "Verification (in Kibana Discover):"
echo "  Index: gmail_emails-999999"
echo "  High risk: suspicion_score >= 40"
echo "  Reply-To mismatch: explanations : \"Reply-To domain differs*\""
echo "  Shorteners: explanations : \"Uses link shortener*\""
echo "  Attachments: explanations : \"Contains risky attachment*\""
echo "  Control: _id : \"tc7-ok-control\" (should NOT be suspicious)"
echo ""
echo "Domain Enrichment Setup (for tc6 and production use):"
echo ""
echo "  Option 1: Seed test domain manually:"
echo "  curl -X PUT \"$ES_URL/domain_enrich/_doc/new-hire-team-hr.com\" \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"domain\":\"new-hire-team-hr.com\",\"created_at\":\"'"\$(date -u -d '7 days ago' --iso-8601=seconds 2>/dev/null || date -u -v-7d +%Y-%m-%dT%H:%M:%S%z 2>/dev/null || echo '2024-01-01T00:00:00Z')"'\",\"age_days\":7,\"risk_hint\":\"very_young\",\"enriched_at\":\"'"\$(date -u --iso-8601=seconds 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%S%z 2>/dev/null || echo '2024-01-08T00:00:00Z')"'\"}'"
echo ""
echo "  Option 2: Run domain enrichment worker (recommended):"
echo "  # Install dependencies"
echo "  pip install -r services/workers/requirements.txt"
echo ""
echo "  # Enrich all domains once"
echo "  python services/workers/domain_enrich.py --once"
echo ""
echo "  # Or run continuously (daemon mode, 1 hour interval)"
echo "  python services/workers/domain_enrich.py --daemon --interval 3600"
echo ""
echo "  After enriching, re-execute policy and re-index tc6:"
echo "  curl -X POST \"$ES_URL/_enrich/policy/domain_age_policy/_execute\""
echo "  curl -X DELETE \"$ES_URL/gmail_emails-999999/_doc/tc6-young-domain\""
echo "  python scripts/generate_test_emails.py"
echo ""
echo "API Endpoints:"
echo "  GET  /emails/{id}/risk-advice - Get risk assessment"
echo "  POST /emails/{id}/risk-feedback - Submit user feedback"
echo ""
echo "Next Steps:"
echo "  1. ✅ Query test index in Kibana: gmail_emails-999999"
echo "  2. ⚙️  Set up domain enrichment worker (see above)"
echo "  3. 📊 Monitor Prometheus metrics: email_risk_served_total, email_risk_feedback_total"
echo "  4. 📈 Create Kibana dashboards for signal analytics"
echo "  5. 🧪 Test with real production emails"
echo ""
echo "Documentation:"
echo "  • Domain Enrichment: docs/DOMAIN_ENRICHMENT_WORKER.md"
echo "  • Test Generator: docs/TEST_EMAIL_GENERATOR.md"
echo "  • E2E Tests: apps/web/tests/e2e/README-email-risk.md"
echo "  • v3.1 Summary: docs/EMAIL_RISK_V3.1_SUMMARY.md"
echo ""
