#!/bin/bash
# Weekly Git History Sanity Check
# Verifies no dbt artifacts have snuck back into remote history
# Run: ./analytics/ops/weekly-history-check.sh

set -e

echo "🔍 Weekly Git History Sanity Check"
echo "=================================="
echo ""

# Fetch latest remote state
echo "📡 Fetching latest remote refs..."
git fetch --all --quiet

# Check for dbt_packages in remote history
echo "🔎 Scanning remote history for dbt_packages..."
PACKAGES_COUNT=$(git log --remotes --format=%H | \
  xargs -I {} git ls-tree -r --name-only {} 2>/dev/null | \
  grep -c "dbt_packages" || echo "0")

# Check for package-lock.yml in remote history  
echo "🔎 Scanning remote history for package-lock.yml..."
LOCKFILE_COUNT=$(git log --remotes --format=%H | \
  xargs -I {} git ls-tree -r --name-only {} 2>/dev/null | \
  grep -c "package-lock.yml" || echo "0")

# Report results
echo ""
echo "📊 Results:"
echo "  dbt_packages files:   $PACKAGES_COUNT"
echo "  package-lock.yml:     $LOCKFILE_COUNT"
echo ""

if [ "$PACKAGES_COUNT" -eq 0 ] && [ "$LOCKFILE_COUNT" -eq 0 ]; then
  echo "✅ History is clean! No artifacts found."
  echo ""
  echo "📅 Last checked: $(date +"%Y-%m-%d %H:%M:%S")"
  exit 0
else
  echo "❌ WARNING: Artifacts detected in history!"
  echo ""
  echo "🚨 Action Required:"
  echo "  1. Identify which commit introduced them:"
  echo "     git log --remotes --all -- '**/dbt_packages/**' '**/package-lock.yml'"
  echo ""
  echo "  2. Check if it's in a PR or feature branch"
  echo "  3. Review docs/HISTORY-CLEANUP.md for remediation"
  echo ""
  exit 1
fi
