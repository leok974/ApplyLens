#!/usr/bin/env bash
# verify-ci.sh - Verify all required CI workflows are green on main
set -euo pipefail

echo "==> Checking latest workflow runs on main"
gh run list --branch main --limit 10

# Required workflows to check
REQUIRED=("API Tests" "CI" "Automation Tests")
FAIL=0

for W in "${REQUIRED[@]}"; do
  echo "==> Checking workflow: $W"
  ID=$(gh run list --branch main --workflow "$W" --limit 1 --json databaseId,status,conclusion \
      --jq '.[0] | "\(.databaseId) \(.status) \(.conclusion)"' 2>/dev/null || echo "")
  
  if [[ -z "$ID" ]]; then
    echo "⚠️  No runs found for workflow: $W"
    FAIL=1
    continue
  fi
  
  echo "   $W: $ID"
  if [[ "$ID" != *"completed success"* ]]; then
    echo "❌ Workflow $W is not green"
    FAIL=1
  else
    echo "✅ Workflow $W is green"
  fi
done

if [[ $FAIL -ne 0 ]]; then
  echo ""
  echo "❌ Some required workflows are not green."
  echo "Re-running latest failed checks for visibility..."
  
  # Re-run last failed run (no-op if already green)
  gh run list --branch main --limit 5 --json databaseId,conclusion \
    --jq '.[] | select(.conclusion!="success") | .databaseId' \
    | xargs -I {} gh run rerun {} 2>/dev/null || true
  
  exit 1
fi

echo ""
echo "✅ All required workflows are green on main."
exit 0
