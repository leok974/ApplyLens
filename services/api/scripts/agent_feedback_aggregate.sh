#!/usr/bin/env bash
#
# Agent V2 Feedback Aggregation Nightly Job
#
# Calls the protected /api/v2/agent/feedback/aggregate endpoint
# to process user feedback and update preferences.
#
# Runs daily to keep the learning loop fresh.

set -euo pipefail

echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Starting agent feedback aggregation..."

# Call the aggregate endpoint with shared secret
curl -X POST \
  -H "Authorization: Bearer ${SHARED_SECRET}" \
  -H "Content-Type: application/json" \
  -f \
  http://applylens-api-prod:8003/api/v2/agent/feedback/aggregate \
  || {
    echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] ERROR: Feedback aggregation failed"
    exit 1
  }

echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Agent feedback aggregation completed successfully"
