# Root /tests Directory - E2E Tests

**TODO(legacy?)**: Flagged in REPO_AUDIT_PHASE1.md for review.

**Current Status**: Contains 18 E2E test files using Playwright.

This directory may be:
- Legacy test location (now tests are in `apps/web/tests` and `apps/web/e2e`)
- Still active and serving a purpose
- Or duplicate of newer test structure

**Current Contents**:
- `tests/e2e/*.spec.ts` - E2E test files
- `tests/e2e/utils/` - Test utilities
- `tests/setup/` - Test setup/fixtures

**Action Required**: Determine if this is:
1. Duplicate of `apps/web/tests` or `apps/web/e2e` and can be consolidated
2. Different test suite with specific purpose
3. Legacy and can be removed if tests migrated

**Review By**: 2025-12-31

**Compare with**:
- `apps/web/tests/` - Current test directory?
- `apps/web/e2e/` - Current E2E directory?
