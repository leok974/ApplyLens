#!/usr/bin/env bash
set -euo pipefail

SECRET_ID="${1:-}"
NEW_VALUE="${2:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"

if [[ -z "$SECRET_ID" || -z "$NEW_VALUE" ]]; then
  echo "Usage: $0 SECRET_ID NEW_VALUE"
  echo "  (AWS_REGION defaults to us-east-1)"
  exit 1
fi

echo "→ Updating AWS Secrets Manager: $SECRET_ID (region: $AWS_REGION)"
aws secretsmanager put-secret-value \
  --region "$AWS_REGION" \
  --secret-id "$SECRET_ID" \
  --secret-string "$NEW_VALUE"

echo "✓ Secret rotated successfully."
