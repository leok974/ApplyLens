# Changelog

All notable changes to ApplyLens will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.3] - 2025-11-24

### ✨ Features

#### Persistent Follow-up State with Progress Tracking
- **Database schema** - New `followup_queue_state` table for persistent done/not-done state
  - Composite primary key: `(user_id, thread_id)`
  - Columns: `application_id`, `is_done`, `done_at`, `updated_at`
  - Migration: `09308884b950_add_followup_queue_state_table.py`
  - Reference: `services/api/alembic/versions/09308884b950_add_followup_queue_state_table.py`, `services/api/app/models.py`

- **POST /v2/agent/followups/state endpoint** - Update done state for follow-up items
  - Request: `{thread_id: str, application_id?: int, is_done: bool}`
  - Response: `{ok: true}`
  - Upserts state row (creates new or updates existing)
  - Sets `done_at` timestamp when transitioning to done
  - Resets `done_at` when unmarking
  - Requires authentication (uses session user_id)
  - Reference: `services/api/app/routers/agent.py`

- **Enhanced queue response** - Progress tracking in queue metadata
  - Extended `QueueMeta` with `done_count` and `remaining_count`
  - GET /v2/agent/followup-queue now fetches state rows and applies `is_done` to items
  - Reference: `services/api/app/schemas_agent.py`, `services/api/app/routers/agent.py`

- **Progress bar UI** - Visual completion tracking
  - Header shows: "{done_count} / {total} done" with percentage
  - Green progress bar with smooth transition animation
  - Real-time updates when marking items done/not-done
  - Reference: `apps/web/src/pages/FollowupQueue.tsx`

- **Optimistic UI updates** - Instant feedback with rollback on error
  - `markDone(item, isDone)` now async with API persistence
  - Optimistically updates local state before API call
  - Rolls back changes and shows error toast on API failure
  - Success/error toast notifications using sonner
  - Reference: `apps/web/src/hooks/useFollowupQueue.ts`

- **Analytics & Metrics** - Track completion behavior
  - Prometheus metric: `applylens_followup_queue_item_done_total`
  - Increments when item transitions to done state
  - Reference: `services/api/app/metrics.py`

### 🧪 Testing

- **Backend state tests** - CRUD operations for followup_queue_state
  - 4 tests: create state, update to done, update to not-done, auth required
  - Reference: `services/api/tests/test_followup_state.py`

- **Backend queue tests** - State application in queue endpoint
  - New test: `test_followup_queue_applies_done_state`
  - Verifies done_count/remaining_count calculations
  - Validates is_done field applied correctly to items
  - Reference: `services/api/tests/test_agent_followup_queue.py`

- **Frontend tests** - Progress rendering and done toggle
  - Page tests verify progress bar with correct counts and percentage
  - Component tests validate markDone called with (item, isDone) signature
  - Reference: `apps/web/src/pages/__tests__/FollowupQueue.test.tsx`, `apps/web/src/components/followups/__tests__/FollowupQueueList.test.tsx`

### 📚 Documentation

- Updated schemas: `QueueMeta` now includes `done_count`, `remaining_count`
- New schema: `FollowupStateUpdate` for state endpoint
- Updated hook interface: `markDone` now accepts `(item, isDone)` instead of `(item)`

## [0.6.2] - 2025-11-24

### ✨ Features

#### Follow-up Queue – Unified View of Mailbox Followups + Tracker Applications
- **POST /v2/agent/followup-queue endpoint** - Merge mailbox followups with Tracker applications
  - Calls Agent V2 orchestrator with "followups" intent in preview_only mode
  - Queries applications where `needs_followup = true` (has thread_id + status in {applied, hr_screen, interview})
  - Merges threads and applications by `thread_id` with priority boosting
  - Priority system: Items with applications get 70+ priority, orphan apps get 60
  - Sorts by priority descending for optimal follow-up workflow
  - Returns: `{status, queue_meta: {total, time_window_days}, items: [{thread_id, application_id?, priority, reason_tags[], company?, role?, subject, snippet, last_message_at, status?, gmail_url, is_done}]}`
  - Reference: `services/api/app/routers/agent.py`, `services/api/app/agent/orchestrator.py`

- **Follow-up Queue page** - Unified UI for follow-up management
  - Route: `/followups` with navigation entry in AppHeader
  - **Split layout**: Left sidebar (queue list) + right panel (thread details)
  - **Queue list component**: Company/role display, status badges, age chips, priority indicators
  - **Done toggle**: Mark items complete with visual feedback (opacity/strikethrough)
  - **Details panel**: Company/role info, status, last update, priority, reason tags
  - **Action buttons**: Open in Gmail, Open in Tracker (when application_id present)
  - Loading skeleton, empty state ("All caught up!"), error handling
  - Reference: `apps/web/src/pages/FollowupQueue.tsx`, `apps/web/src/components/followups/FollowupQueueList.tsx`

- **useFollowupQueue hook** - State management for queue
  - Auto-loads queue on mount with `loadQueue()`
  - `markDone(item)`: Toggles `is_done` locally (client-side only)
  - Returns: items, queueMeta, isLoading, error, selectedItem, setSelectedItem, markDone, refresh
  - Reference: `apps/web/src/hooks/useFollowupQueue.ts`

- **Analytics & Metrics** - Usage tracking for follow-up queue
  - Prometheus metric: `applylens_followup_queue_requested_total`
  - Reference: `services/api/app/metrics.py`

### 🧪 Testing

- **Backend unit tests** - Comprehensive test coverage for queue endpoint
  - 4 tests for `/v2/agent/followup-queue` endpoint: merging, orphan apps, counts, sorting
  - Reference: `services/api/tests/test_agent_followup_queue.py`

- **Frontend unit tests** - React Testing Library tests for UI
  - Component tests for `FollowupQueueList`: badges, chips, done toggle, selection
  - Page tests for `FollowupQueue`: loading, empty state, error handling, list rendering
  - Reference: `apps/web/src/components/followups/__tests__/FollowupQueueList.test.tsx`, `apps/web/src/pages/__tests__/FollowupQueue.test.tsx`

- **E2E tests** - Production-safe Playwright tests
  - Navigation to `/followups`, row selection, done toggle interaction
  - `test.skip()` when no queue items present for production safety
  - Reference: `apps/web/tests/e2e/followup-queue.spec.ts`

### 📚 Documentation

- Added schemas: `QueueMeta`, `QueueItem`, `FollowupQueueRequest`, `FollowupQueueResponse`
- Priority-based workflow: Applications boost priority for better triage
- Badges: Status (applied/hr_screen/interview), Priority (High/Medium/Low), Age (Xd ago)
- Dark-first Banana theme with zinc palette for consistent UI

---

## [0.6.1] - 2025-11-24

### ✨ Features

#### Thread Viewer – AI-Powered Follow-up Drafts
- **POST /v2/agent/followup-draft endpoint** - Generate AI follow-up emails for recruiter threads
  - Uses Agent V2 orchestrator with thread_detail tool for context
  - Integrates with Ollama (llama3:latest) primary, OpenAI (gpt-4o-mini) fallback
  - Accepts `user_id`, `thread_id`, `application_id` (optional), `mode="preview_only"`
  - Returns JSON: `{subject, body}` for professional recruiter follow-ups
  - Reference: `services/api/app/routers/agent.py`, `services/api/app/agent/orchestrator.py`

- **Thread Viewer "Draft follow-up" button** - UI integration for draft generation
  - Purple-themed button with Sparkles icon in Thread Viewer header
  - Displays AI-generated draft in purple card with subject/body sections
  - **Copy to clipboard** actions: Full draft (subject + body) or body only
  - Error handling with toast notifications
  - Auto-clears draft on dismiss
  - Reference: `apps/web/src/components/mail/ThreadViewer.tsx`, `apps/web/src/hooks/useFollowupDraft.ts`

- **Analytics & Metrics** - Usage tracking for follow-up draft feature
  - Prometheus metric: `applylens_followup_draft_requested_total{source="thread_viewer"}`
  - Analytics events: `followup_draft_generated`, `followup_draft_error`, `followup_draft_copied`, `followup_draft_body_copied`
  - Reference: `services/api/app/metrics.py`, `apps/web/src/lib/analytics.ts`

### 🧪 Testing

- **Backend unit tests** - Comprehensive test coverage for draft endpoint
  - 5 tests for `/v2/agent/followup-draft` endpoint
  - 3 tests for `orchestrator.draft_followup()` method
  - Reference: `services/api/tests/test_agent_followup_draft.py`

- **Frontend unit tests** - React Testing Library tests for UI
  - 8 tests covering button render, draft generation, clipboard copy, error handling
  - Reference: `apps/web/src/test/ThreadViewer.followupDraft.test.tsx`

### 📚 Documentation

- Added schemas: `FollowupDraft`, `FollowupDraftRequest`, `FollowupDraftResponse`
- LLM integration: Temperature 0.3, JSON format enforced
- Clipboard API integration for copy actions
- Purple theming for AI-generated content (consistent with Agent V2)

---

## [0.5.0] - 2025-01-27

### 🐛 Critical Fixes

#### Authentication & Session Management
- **Fixed /api/auth/logout returning 500 error** - Resolved naming conflict between SQLAlchemy `Session` class and custom `Session` model
  - Root cause: `from app.models import Session` in auth router conflicted with SQLAlchemy's Session
  - Solution: Enforced alias pattern `from app.models import Session as UserSession` throughout codebase
  - Impact: Logout now returns 200, properly deletes session, and clears cookies
  - Reference: `app/routers/auth.py` Line 7, `docs/DOCKER_SETUP_COMPLETE.md`

- **Fixed browser crashes on logout** - Eliminated hard page reloads (`window.location.href`) in SPA navigation
  - Root cause: Hard reloads during auth state changes caused browser to abort in-flight requests
  - Solution: Replaced all `window.location.href = '/welcome'` with React Router `navigate('/welcome')`
  - Files fixed: `Settings.tsx`, `AppHeader.tsx`, `Landing.tsx`
  - Impact: Smooth logout flow, no crashes, better UX

#### CSRF Protection & API Integration
- **Implemented CSRF token bootstrap** - Ensures CSRF token is acquired before any mutating requests
  - Added `ensureCsrf()` utility that fetches `/api/auth/csrf` on first call
  - Created `apiFetch()` wrapper that auto-injects CSRF token via `X-CSRF-Token` header
  - All POST/PUT/DELETE requests now use CSRF-aware fetch
  - Reference: `apps/web/src/api/apiFetch.ts`

- **Fixed CSRF middleware exemptions** - Dev routes properly bypass CSRF checks
  - Added `/api/dev/*` to CSRF exempt paths
  - Fixed route precedence: dev routers registered before auth middleware
  - Reference: `services/api/app/main.py`

### ✨ Features

#### Deep Linking & Navigation
- **Added inbox deep-linking** - Support for `/inbox?open=<thread_id>` URLs
  - Opens specific thread from URL parameter
  - Enables email notifications with direct links to threads
  - Handles missing/invalid thread IDs gracefully
  - Reference: `apps/web/src/pages/Inbox.tsx`

#### Developer Experience
- **Dev routes precedence fix** - Dev endpoints now consistently accessible
  - Moved dev router registration before rate limiting and auth middleware
  - Added `ALLOW_DEV_ROUTES` environment variable control
  - Seed endpoints (`/api/dev/seed-*`) work reliably in development
  - Reference: `services/api/app/main.py` Lines 260-263

### 🧪 Testing & Quality

#### E2E Test Hardening
- **Playwright configuration improvements**
  - Changed trace capture: `"on-first-retry"` (more efficient than `"retain-on-failure"`)
  - Enabled video capture: `"retain-on-failure"` (always capture failed tests)
  - Screenshot on failure: `"only-on-failure"` (unchanged)
  - Reference: `apps/web/playwright.config.ts`

- **Console listeners for better debugging**
  - Custom console listeners capture browser logs during tests
  - Helps diagnose failures with full context
  - Reference: `apps/web/tests/setup/console-listeners.ts`

- **Core test suite established**
  - `auth.demo.spec.ts` - Demo login flow
  - `auth.logout.spec.ts` - Original logout test
  - `auth.logout.regression.spec.ts` - Comprehensive regression suite (2 tests)
  - `search-populates.spec.ts` - Search functionality
  - All tests passing ✅

#### Regression Tests
- **API Unit Test** - `tests/test_auth_logout.py`
  - `test_logout_session_model_query_works()` - Validates Session model can be queried
  - `test_session_alias_pattern()` - Documents correct import pattern

- **UI E2E Tests** - `tests/e2e/auth.logout.regression.spec.ts`
  - `logout returns 200, redirects to /welcome, and clears session` - Main regression test
  - `guard redirects unauthenticated users to /welcome` - Auth guard behavior
  - Validates: 200 response, no browser crash, session cleared, soft navigation

### 📚 Documentation

- **Created E2E_GUIDE.md** (500+ lines)
  - Comprehensive testing guide
  - Environment variables reference
  - Architecture explanation
  - Common failures & solutions (CSRF, rate limits, dev routes, sessions, Nginx, database)
  - Test categories with tags (@devOnly, @prodSafe)
  - Debugging tips (headed mode, trace viewer, reports, workers)
  - Writing new tests with template
  - CI integration examples
  - Performance optimization tips
  - Reference: `apps/web/docs/E2E_GUIDE.md`

- **Created DOCKER_SETUP_COMPLETE.md** (400+ lines)
  - Complete Docker setup documentation
  - Services overview (PostgreSQL, Elasticsearch, FastAPI, React, Nginx)
  - Known issues & fixes:
    1. Logout 500 error (Session naming conflict)
    2. Hard page reloads (window.location → navigate)
    3. CSRF bootstrap (ensureCsrf + apiFetch)
  - Configuration details (API + Frontend env vars)
  - Nginx configuration (same-origin proxy)
  - Testing instructions
  - **5 Best Practices** (critical rules):
    1. Never use hard reloads in SPA
    2. Always alias SQLAlchemy Session
    3. Use CSRF-aware fetch
    4. Test-friendly rate limits in dev
    5. Dev routes only in development
  - Troubleshooting guide
  - Reference: `docs/DOCKER_SETUP_COMPLETE.md`

### 🔧 Infrastructure

#### Nginx Configuration
- **Same-origin proxy validated** - All API requests proxied through Nginx
  - Frontend: `http://nginx:80` → `http://web:80`
  - API: `http://nginx:80/api/*` → `http://api:8003/*`
  - Single default_server prevents conflicts
  - CSRF tokens work correctly with same-origin
  - Reference: `infra/nginx/nginx.conf`

#### Rate Limiting
- **Development-friendly defaults**
  - Rate limit: 60 requests / 60 seconds (configurable)
  - Allows rapid E2E test execution
  - Production should use stricter limits
  - Reference: `services/api/app/core/limiter.py`

### 🔒 Security

#### Session Management
- **Improved session cleanup**
  - Logout properly deletes session from database
  - Session cookie cleared with `max_age=-1` and `expires` in past
  - No orphaned sessions in database
  - Reference: `app/routers/auth.py` `/auth/logout` endpoint

#### CSRF Protection
- **Comprehensive CSRF coverage**
  - All mutating endpoints require CSRF token
  - Dev routes properly exempted (`/api/dev/*`)
  - Health/status endpoints exempted (`/api/health`, `/api/healthz`)
  - Token validated via `X-CSRF-Token` header
  - Reference: `services/api/app/core/csrf.py`

### 🧹 Code Quality

#### Cleanup
- **Removed temporary debug instrumentation**
  - Deleted `nav-debug.ts` (temporary navigation debugging)
  - Removed all debug hooks from components:
    - `LoginGuard.tsx` - Removed `(window as any).__rr_nav__` hook
    - `Settings.tsx` - Removed debug navigation wrapper
    - `AppHeader.tsx` - Removed debug navigation wrapper
    - `Landing.tsx` - Removed debug navigation wrapper
  - Kept useful console.log statements for troubleshooting
  - Production-ready codebase

#### Best Practices Enforced
- **SQLAlchemy Session aliasing**
  - Pattern: `from sqlalchemy.orm import Session as DBSession`
  - Pattern: `from app.models import Session as UserSession`
  - Never import Session without alias in routers
  - Prevents type confusion and runtime errors

- **React Router navigation**
  - Always use `navigate()` from `useNavigate()` hook
  - Never use `window.location.href` for internal navigation
  - Prevents browser crashes and maintains SPA state

- **CSRF-aware API calls**
  - Always use `apiFetch()` wrapper for mutating requests
  - Automatically injects CSRF token
  - Handles token bootstrap on first call

### 📊 Metrics & Observability

- Rate limiter logs: Request counts and limit violations
- CSRF failures logged with details for debugging
- Auth failures tracked (401/403 responses)
- Session creation/deletion logged
- Reference: `services/api/app/logging.yaml`

---

## [0.4.64] - 2025-01-26

### Previous Release
- Theme-aware select fields for light/dark modes
- Various UI improvements and bug fixes

---

## Migration Notes

### Upgrading from 0.4.x to 0.5.0

#### Backend Changes
1. **Environment Variables**
   - Add `ALLOW_DEV_ROUTES=1` for development environments
   - Set `ALLOW_DEV_ROUTES=0` for production
   - Verify `DATABASE_URL` includes correct host (use `db` for Docker, `localhost` for local)

2. **Code Changes**
   - If you have custom routers, ensure Session imports use aliases:
     ```python
     # ❌ WRONG
     from app.models import Session
     from sqlalchemy.orm import Session

     # ✅ CORRECT
     from sqlalchemy.orm import Session as DBSession
     from app.models import Session as UserSession
     ```

3. **Database**
   - No schema changes in this release
   - Existing sessions remain valid

#### Frontend Changes
1. **API Calls**
   - Use `apiFetch()` for all POST/PUT/DELETE requests
   - CSRF token automatically managed
   - Example:
     ```typescript
     // ❌ OLD
     fetch('/api/auth/logout', { method: 'POST' })

     // ✅ NEW
     import { apiFetch } from '@/api/apiFetch'
     apiFetch('/api/auth/logout', { method: 'POST' })
     ```

2. **Navigation**
   - Replace hard reloads with React Router navigation:
     ```typescript
     // ❌ OLD
     window.location.href = '/welcome'

     // ✅ NEW
     import { useNavigate } from 'react-router-dom'
     const navigate = useNavigate()
     navigate('/welcome')
     ```

#### Testing
1. **E2E Tests**
   - Review `apps/web/docs/E2E_GUIDE.md` for testing patterns
   - Use environment variables for configuration:
     - `E2E_BASE_URL` - Base URL for tests (default: http://127.0.0.1:8888)
     - `E2E_API` - API endpoint (default: http://127.0.0.1:8888/api)
     - `USE_SMOKE_SETUP` - Use fast smoke setup (true/false)
     - `SEED_COUNT` - Number of threads to seed (default: 20)

2. **Running Tests**
   ```bash
   # Smoke tests (fast)
   npm run test:smoke

   # Full E2E suite
   E2E_BASE_URL=http://127.0.0.1:8888 \
   E2E_API=http://127.0.0.1:8888/api \
   USE_SMOKE_SETUP=true \
   npm run test:e2e -- --workers=4

   # Regression tests only
   npx playwright test tests/e2e/auth.logout.regression.spec.ts
   ```

#### Docker Compose
1. **Verify Services**
   ```bash
   docker compose ps
   # Should show: db, es, api, web, nginx all healthy
   ```

2. **Restart After Update**
   ```bash
   docker compose pull
   docker compose up -d
   docker compose restart nginx  # If API container IP changed
   ```

3. **Health Checks**
   ```bash
   # API health
   curl http://localhost:8888/api/healthz

   # Web health
   curl http://localhost:8888/health

   # CSRF token (should return cookies)
   curl -v http://localhost:8888/api/auth/csrf
   ```

---

## Rollback Instructions

### Rolling Back from 0.5.0 to 0.4.64

If you encounter issues with 0.5.0, follow these steps to roll back:

1. **Stop Services**
   ```bash
   docker compose down
   ```

2. **Checkout Previous Version**
   ```bash
   git checkout v0.4.64
   # or
   git checkout <previous-commit-hash>
   ```

3. **Rebuild Images** (if needed)
   ```bash
   docker compose build --no-cache
   ```

4. **Restart Services**
   ```bash
   docker compose up -d
   ```

5. **Verify Health**
   ```bash
   curl http://localhost:8888/api/healthz
   curl http://localhost:8888/health
   ```

**Note:** No database migrations in 0.5.0, so rollback is safe.

---

## Known Issues

### Fixed in This Release
- ✅ Logout 500 error (Session naming conflict)
- ✅ Browser crashes on logout (hard reload)
- ✅ CSRF token missing on first request
- ✅ Dev routes inaccessible due to middleware precedence

### Outstanding Issues
- None reported

---

## Contributors

- Internal team: Logout bug investigation, fixes, testing, and documentation

---

## Links

- [E2E Testing Guide](apps/web/docs/E2E_GUIDE.md)
- [Docker Setup Guide](docs/DOCKER_SETUP_COMPLETE.md)
- [GitHub Repository](https://github.com/leok974/ApplyLens)
- [Issue Tracker](https://github.com/leok974/ApplyLens/issues)

---

**Full Changelog**: https://github.com/leok974/ApplyLens/compare/v0.4.64...v0.5.0
