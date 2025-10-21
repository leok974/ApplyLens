#!/usr/bin/env bash
set -euo pipefail

SECRET_ID="${1:-}"
NEW_VALUE="${2:-}"

if [[ -z "$SECRET_ID" || -z "$NEW_VALUE" ]]; then
  echo "Usage: $0 SECRET_ID NEW_VALUE"
  exit 1
fi

echo "→ Adding new version to GCP Secret Manager: $SECRET_ID"
echo -n "$NEW_VALUE" | gcloud secrets versions add "$SECRET_ID" --data-file=-

echo "✓ New version created. Latest enabled:"
gcloud secrets versions list "$SECRET_ID" --filter="state=ENABLED" --limit=1
