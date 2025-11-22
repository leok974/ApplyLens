#!/usr/bin/env bash
set -euo pipefail

# Pre-commit hook to prevent SQLAlchemy Session naming conflicts
# This enforces the "Session as DBSession" / "Session as UserSession" pattern
# that prevents the logout 500 error.

echo "🔍 Checking for disallowed SQLAlchemy Session imports..."

# 1) Forbid unaliased ORM Session imports in routers (must alias to DBSession)
violations1=$(grep -rEn --include="*.py" \
  'from\s+sqlalchemy\.orm\s+import\s+.*Session' \
  services/api/app/routers 2>/dev/null | \
  grep -v 'as DBSession' || true)

# 2) Forbid unaliased Model Session imports in routers (must alias to UserSession)
violations2=$(grep -rEn --include="*.py" \
  'from\s+app\.models\s+import\s+.*Session' \
  services/api/app/routers 2>/dev/null | \
  grep -v 'as UserSession' || true)

# 3) Forbid bare Session type annotations in router functions
violations3=$(grep -rEn --include="*.py" \
  'def\s+\w+.*\(.*db\s*:\s*Session[^a-zA-Z]' \
  services/api/app/routers 2>/dev/null || true)

if [[ -n "$violations1" ]]; then
  echo ""
  echo "❌ ERROR: Unaliased SQLAlchemy Session import found in routers:"
  echo "$violations1"
  echo ""
  echo "✅ REQUIRED: Use 'from sqlalchemy.orm import Session as DBSession'"
  echo ""
  exit 1
fi

if [[ -n "$violations2" ]]; then
  echo ""
  echo "❌ ERROR: Unaliased app.models Session import found in routers:"
  echo "$violations2"
  echo ""
  echo "✅ REQUIRED: Use 'from app.models import Session as UserSession'"
  echo ""
  exit 1
fi

if [[ -n "$violations3" ]]; then
  echo ""
  echo "❌ ERROR: Bare 'Session' type annotation found in routers:"
  echo "$violations3"
  echo ""
  echo "✅ REQUIRED: Use 'db: DBSession' (not 'db: Session')"
  echo ""
  exit 1
fi

echo "✅ SQLAlchemy Session import checks passed."
exit 0
