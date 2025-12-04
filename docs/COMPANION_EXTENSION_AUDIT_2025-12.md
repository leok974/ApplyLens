# ApplyLens Companion / Extension Audit - December 2025

**Audit Date**: December 3, 2025
**Auditor**: GitHub Copilot Workspace (automated)
**Scope**: Extension code, Backend API, Web UI, Build/Deployment infrastructure

---

## 1. Overview

The **ApplyLens Companion** is a Manifest V3 Chrome extension designed to:
- Autofill job application forms (Greenhouse, Lever, Workday, SmartRecruiters, Ashby)
- Draft personalized LinkedIn recruiter Direct Messages
- Log application and outreach activity to the ApplyLens backend
- Learn user preferences through a **multi-armed bandit** system for style optimization

**Current Design Pattern**:
```
User → ATS Page → Content Script → Service Worker → Backend API
                      ↓                    ↓
                  DOM manipulation    Message passing
                      ↓                    ↓
                  In-page panel      chrome.storage
```

**Key Technologies**:
- **Extension**: Vanilla JS (zero-bundle), Manifest V3, IndexedDB for local state
- **Backend**: FastAPI (Python), endpoints under `/api/extension/*` and `/api/profile/me`
- **Web UI**: React (Vite), feature-gated behind `VITE_FEATURE_COMPANION`

---

## 2. Extension Code Status

### Message Types & Handlers

| Message Type | Sent From | Handled By | Backend Endpoint | Status |
|---|---|---|---|---|
| `GET_PROFILE` | popup.js | sw.js | `GET /api/profile/me` | ✅ Present |
| `GEN_FORM_ANSWERS` | popup.js | sw.js | `POST /api/extension/generate-form-answers` | ✅ Present |
| `LOG_APPLICATION` | popup.js | sw.js | `POST /api/extension/applications` | ✅ Present |
| `GEN_DM` | popup.js | sw.js | `POST /api/extension/generate-recruiter-dm` | ✅ Present |
| `LOG_OUTREACH` | popup.js | sw.js | `POST /api/extension/outreach` | ✅ Present |
| `SCAN_AND_SUGGEST` | popup.js | content.js | (client-side) | ✅ Present |
| `GET_HISTORY` | popup.js | sw.js | chrome.storage.local | ✅ Present |

**Additional Content Script Messages** (not in service worker):
- Content script directly fetches from `/api/extension/learning/profile`
- Content script directly POSTs to `/api/extension/learning/sync`
- Content script directly POSTs to `/api/extension/feedback/autofill`

### Capability Assessment

| Capability | Status | Evidence | Notes |
|---|---|---|---|
| **Profile fetch** | ✅ Present | `sw.js:30`, `GET_PROFILE` message | Returns user profile data for autofill |
| **Form scanning** | ✅ Present | `content.js:67-88`, `scanFields()` | Detects textarea, text/email/url/search inputs with labels |
| **Form autofill** | ✅ Present | `content.js:195-205`, `fetchFormAnswers()` | Calls backend, displays in-page panel with accept/edit |
| **Application logging** | ✅ Present | `sw.js:37-40`, `LOG_APPLICATION` | Stores in backend + local history (max 50) |
| **Outreach/DM helpers** | ✅ Present | `sw.js:45-48`, `popup.js:76-96` | Generates DM, copies to clipboard, logs outreach |
| **Error handling** | ⚠️ Partial | `content.js`, no dedicated error UI | Errors logged to console, no user-facing feedback in panel |
| **Status UI in content** | ⚠️ Partial | Panel shows fields, no API health indicator | Panel doesn't show "connecting..." or "API offline" |
| **Config (dev vs prod)** | ✅ Present | `config.js:2-5` | Auto-detects: prod=`https://api.applylens.app`, dev=`http://localhost:8003` |
| **Learning loop** | ✅ Present | `learning/client.js`, `learning/formMemory.js` | Tracks edits, syncs to backend, stores locally in IndexedDB |
| **Bandit system** | ✅ Present | `content.js:100-161`, epsilon-greedy selection | Selects from multiple AI styles, tracks helpful_ratio |
| **Guardrails** | ✅ Present | `guardrails.js`, sanitizeGeneratedContent | PII redaction, char limits, URL validation |

### Gaps - Extension UI/UX

1. **No in-page API health indicator**: Panel doesn't show connection status or loading spinner while waiting for backend.
   - **File**: `content.js` (panel rendering logic around line 300-400)
   - **Impact**: User doesn't know if delay is network vs. generation time

2. **Console-only error messages**: Failed API calls log to console but don't show user-friendly errors in the panel.
   - **File**: `content.js:195-205` (fetchFormAnswers), no catch with UI update
   - **Impact**: User sees nothing when backend is down

3. **Popup doesn't retry on SW init failure**: `popup.js:13-21` implements retry for service worker, but only 3 attempts with 100ms delay.
   - **File**: `popup.js:13-21`
   - **Impact**: If SW is slow to start, popup may show "offline" incorrectly

4. **No feedback for "Fill All" success/failure**: Content script fills fields but doesn't show "Filled 5/7 fields successfully" summary.
   - **File**: `content.js` (after filling logic)
   - **Impact**: User doesn't know if some fields failed to fill

5. **DM draft doesn't show preview before copy**: Popup copies to clipboard immediately without letting user review.
   - **File**: `popup.js:76-96`
   - **Impact**: User can't edit before pasting to LinkedIn

---

## 3. Backend API Status

### Extension-Related Endpoints

| Method | Path | Purpose | Request Body | Response | Used By | Status |
|---|---|---|---|---|---|---|
| GET | `/api/profile/me` | Fetch current user profile | - | `{name, email, ...}` | sw.js (GET_PROFILE) | ⚠️ Unknown (not in extension workspace) |
| POST | `/api/extension/generate-form-answers` | Generate AI answers for form fields | `{job, fields, style_hint?}` | `{answers: [{field_id, value}]}` | content.js | ⚠️ Unknown |
| POST | `/api/extension/applications` | Log job application | `{company, role, url, source, ...}` | `{id}` | sw.js (LOG_APPLICATION) | ⚠️ Unknown |
| POST | `/api/extension/generate-recruiter-dm` | Generate LinkedIn DM | `{profile, job}` | `{message}` | sw.js (GEN_DM), content.js | ⚠️ Unknown |
| POST | `/api/extension/outreach` | Log outreach activity | `{company, recruiter_name, ...}` | `{id}` | sw.js (LOG_OUTREACH) | ⚠️ Unknown |
| POST | `/api/extension/learning/sync` | Send learning events (bandit feedback) | `{host, schema_hash, events: [{suggested_map, final_map, edit_stats}]}` | `{status}` | learning/client.js | ⚠️ Unknown |
| GET | `/api/extension/learning/profile` | Get learned field mappings + style stats | `?host=...&schema_hash=...` | `{profile, selectorMap, styleHint: {preferredStyleId, styleStats}}` | learning.profileClient.js | ⚠️ Unknown |
| POST | `/api/extension/feedback/autofill` | Submit user feedback (helpful/not helpful) | `{host, schema_hash, gen_style_id, helpful, rationale}` | `{status}` | content.js | ⚠️ Unknown |

**Note**: Backend code is outside the extension workspace (`apps/extension-applylens`). Audit cannot confirm implementation details. All endpoints marked as ⚠️ **Unknown** (presence inferred from extension calls + documentation).

### Inferred Backend Requirements (from extension usage)

1. **Profile endpoint** must return:
   - `name` (string)
   - `email` (string)
   - Other fields used for autofill (skills, experience, etc.)

2. **Generate-form-answers endpoint** must:
   - Accept optional `style_hint` object with `preferredStyleId` and `styleStats`
   - Return array of `{field_id, value}` objects
   - Apply guardrails (PII redaction, char limits) server-side

3. **Learning/profile endpoint** must:
   - Return `styleHint` object with bandit statistics:
     ```json
     {
       "preferredStyleId": "formal-concise",
       "styleStats": {
         "chosen": {"styleId": "...", "helpfulRatio": 0.85, "totalRuns": 20},
         "competitors": [{"styleId": "...", "helpfulRatio": 0.72, "totalRuns": 15}]
       }
     }
     ```
   - Support `host` and `schema_hash` query params for form-specific data

4. **Learning/sync endpoint** must:
   - Accept batch of learning events
   - Store `gen_style_id` and `policy` (explore/exploit) for bandit tracking
   - Calculate `helpful_ratio` from edit distances

### Health/Diagnostics Endpoints

**Not found in extension code**. Extension checks `/api/profile/me` for connectivity but doesn't use a dedicated `/api/extension/health` or `/api/ops/diag/health`.

### Backend Tests

**Status**: ⚠️ Unknown (backend tests are outside extension workspace)

**Expected location**: `services/api/tests/` or similar (not visible from `apps/extension-applylens/`)

**Inferred coverage from E2E mocks**:
- E2E tests mock all 8 extension endpoints (see `e2e/*.spec.ts`)
- Extension expects specific response schemas (documented above)
- No evidence of **backend unit tests** visible from extension workspace

### Gaps - Backend

1. **No dedicated health endpoint for extension**: Extension relies on `/api/profile/me` for connectivity check, which requires auth.
   - **Impact**: Can't distinguish "server down" from "user not logged in" from extension popup
   - **Recommendation**: Add `GET /api/extension/health` (no auth required) returning `{"status": "ok"}`

2. **No backend tests visible**: Cannot confirm backend implementation of 8 endpoints.
   - **Impact**: Risk of schema drift between extension expectations and backend reality
   - **Recommendation**: Add backend integration tests for `/api/extension/*` routes

3. **No API versioning**: Extension hardcodes endpoint paths with no version prefix (e.g., `/api/v1/extension/...`).
   - **Impact**: Breaking changes to backend API will break all deployed extensions
   - **Recommendation**: Introduce `/api/v1/extension/*` or use API versioning headers

4. **CORS configuration unclear**: `DEPLOYMENT.md:55-64` mentions CORS config but doesn't show actual production values.
   - **Impact**: Unknown if `chrome-extension://*` is allowed in prod
   - **Recommendation**: Verify `CORS_ALLOW_ORIGINS` includes extension origin or use wildcard for `chrome-extension://`

---

## 4. Web UI Status

### Routes/Pages

| Route | Component | Purpose | Condition | Status |
|---|---|---|---|---|
| `/extension` | (not found) | Extension landing page | Unknown | ⚠️ Missing |
| `/extension/support` | (not found) | Extension support/help | Unknown | ⚠️ Missing |
| `/extension/privacy` | (not found) | Extension privacy policy | Unknown | ⚠️ Missing |
| `/settings/companion` | (not found) | Companion settings | `FLAGS.COMPANION` | ⚠️ Unknown (web app outside workspace) |

**Note**: Web app code is outside extension workspace. Search results show references to these routes in extension docs but cannot confirm implementation.

### Nav Tab for Companion/Extension

**Search results** (from `grep_search` output):
- `VITE_FEATURE_COMPANION` flag exists in docs
- `FLAGS.COMPANION` mentioned in extension docs
- Web app nav structure not visible from extension workspace

**Inferred**:
- Top nav or sidebar has a "Companion" or "Extension" tab
- Gated behind `VITE_FEATURE_COMPANION=1` build-time flag
- Currently **disabled in prod** (per `SUBMISSION_CHECKLIST.md:48`)

### Settings/Companion Page

**Expected content** (from extension docs):
- Install instructions
- Recent applications (from extension logs)
- Recent outreach (from extension logs)
- Bandit settings toggle (enable/disable experimental styles)
- API connectivity status

**Status**: ⚠️ Unknown (web UI code not in extension workspace)

**Evidence of partial implementation**:
- `apps/extension-applylens/SUBMISSION_CHECKLIST.md:42` mentions "Companion settings page (/settings/companion)" as complete
- Extension docs reference settings page for bandit toggle

### Gaps - Web UI

1. **Feature flag disabled in prod**: `VITE_FEATURE_COMPANION=1` not set in production build.
   - **File**: `apps/web/Dockerfile.prod` (likely line 31, based on conversation context)
   - **Impact**: Nav tab hidden, users can't access `/extension` or `/settings/companion` pages
   - **Recommendation**: Set `ARG VITE_FEATURE_COMPANION=1` in Dockerfile.prod and rebuild

2. **No web UI code visible for audit**: Cannot verify existence of:
   - Landing page component (`/extension`)
   - Settings page component (`/settings/companion`)
   - Navigation tab rendering logic
   - **Recommendation**: Audit web app separately (workspace: `apps/web/`)

3. **No status page for extension health**: Web UI doesn't show:
   - Extension install status (detected via browser API)
   - Last sync time from extension
   - Backend API health for extension endpoints
   - **Recommendation**: Add `/settings/companion/status` or integrate into main settings page

---

## 5. Build & Deployment

### Extension Build Process

**Build Script**: `apps/extension-applylens/pack.ps1`

```powershell
# Creates: dist/applylens-companion-YYYYMMDD-HHmmss.zip
# Includes: manifest.json, *.js, *.html, icons/, docs/privacy.md, README.md
# Excludes: node_modules/, test*, e2e/, src/, *.spec.ts, vitest.config.ts
```

**Output**:
- Package size: ~390 KB (per `SUBMISSION_CHECKLIST.md:3`)
- Format: Chrome Web Store compatible ZIP

**NPM Scripts** (from `package.json`):
```json
{
  "test": "vitest run",
  "test:ui": "vitest",
  "e2e": "playwright test -c ./playwright.config.ts",
  "e2e:ext": "playwright test -c ./playwright.with-extension.config.ts",
  "e2e:panel": "playwright test --config=playwright.panel.config.ts",
  "e2e:companion": "playwright test -c ./playwright.config.ts -g \"@companion\""
}
```

**Status**: ✅ Build process well-defined and documented

### CI/CD Integration

**GitHub Actions workflows** (from `docs/GITHUB_WORKFLOWS_AUDIT.md`):

| Workflow | Triggers | Jobs | Status | Notes |
|---|---|---|---|---|
| `e2e-extension.yml` | push, PR | `e2e-extension`, `e2e-companion`, `e2e-extension-summary` | 🔵 Healthy | Consolidated from 2 old workflows |
| (Build/package workflow) | - | - | ❌ Missing | No workflow to build extension ZIP on release |
| (Deploy to CWS workflow) | - | - | ❌ Missing | No workflow to upload to Chrome Web Store |

**Gaps identified**:
1. **No release build workflow**: No CI job to run `pack.ps1` and create GitHub release with ZIP artifact
2. **No automated CWS upload**: Manual upload to Chrome Web Store required
3. **No production smoke tests**: No workflow to test deployed extension against `api.applylens.app`

### Environment Variables & Feature Flags

#### Extension
- **`APPLYLENS_API_BASE`** (code): Auto-detected in `config.js`, not an env var
- **`APPLYLENS_COMPANION_BANDIT_ENABLED`** (docs): Backend env var, not used in extension code
- **`window.__APPLYLENS_BANDIT_ENABLED`** (runtime): Client-side kill switch, set by web UI settings page

#### Backend (inferred)
- **`COMPANION_BANDIT_ENABLED`**: Global kill switch for bandit system (default: `true`)
- **`CORS_ALLOW_ORIGINS`**: Must include `chrome-extension://*` or specific extension ID

#### Web UI
- **`VITE_FEATURE_COMPANION`**: Build-time flag to show/hide Companion nav tab and pages
  - **Dev**: Unknown (web workspace not audited)
  - **Prod**: Currently `0` (disabled), needs to be `1`

### Production Deployment Checklist

**From `SUBMISSION_CHECKLIST.md`**:

✅ **Completed**:
- [x] Extension code built and packaged
- [x] Privacy policy created (`docs/privacy.md`)
- [x] E2E tests passing (9/9 companion tests)
- [x] Store listing JSON prepared

⚠️ **Pending**:
- [ ] Enable `VITE_FEATURE_COMPANION=1` in prod Docker build
- [ ] Upload ZIP to Chrome Web Store
- [ ] Submit for CWS review
- [ ] Test prod extension against `https://api.applylens.app`
- [ ] Cloudflare cache clear for `/api/extension/*` (if caching is enabled)

### Gaps - Build & Deployment

1. **No CI workflow for release builds**:
   - **Impact**: Manual `pack.ps1` execution required for each release
   - **Recommendation**: Create `.github/workflows/extension-release.yml`:
     ```yaml
     on:
       release:
         types: [published]
     jobs:
       build:
         - run: cd apps/extension-applylens && ./pack.ps1
         - uses: actions/upload-artifact@v4
           with:
             name: extension-package
             path: apps/extension-applylens/dist/*.zip
     ```

2. **No automated Chrome Web Store upload**:
   - **Impact**: Manual upload delays releases, prone to human error
   - **Recommendation**: Use [chrome-webstore-upload-cli](https://github.com/fregante/chrome-webstore-upload-cli) in CI

3. **No production smoke tests**:
   - **Impact**: Breaking changes to prod API may not be caught before user complaints
   - **Recommendation**: Add `e2e/prod-companion-smoke.spec.ts` workflow:
     - Runs daily against `https://api.applylens.app`
     - Tests: GET /api/profile/me, POST /api/extension/generate-form-answers
     - Alerts on failure

4. **Docker compose env var not set**: `VITE_FEATURE_COMPANION` not in `docker-compose.prod.yml` or `Dockerfile.prod` (inferred from conversation).
   - **Impact**: Web UI nav tab hidden in production
   - **Recommendation**: Add `ARG VITE_FEATURE_COMPANION=1` to `apps/web/Dockerfile.prod` before npm run build

5. **No rollback plan documented**:
   - **Impact**: If extension v0.2.0 breaks, unclear how to revert users to v0.1.0 in CWS
   - **Recommendation**: Document rollback procedure in `DEPLOYMENT.md`

---

## 6. Gaps vs. Dogfood-Ready v1

### Extension UI/UX Gaps

| Gap | Severity | File(s) | Effort | Description |
|---|---|---|---|---|
| No API health indicator in panel | Medium | `content.js` (panel render) | 2-4 hours | Add "Connecting..." spinner and "API offline" error state to in-page panel |
| Console-only errors | Medium | `content.js:195-205` | 1-2 hours | Catch fetch errors, show user-friendly message in panel ("Failed to generate answers. Retry?") |
| No "Fill All" success summary | Low | `content.js` (fill logic) | 1-2 hours | Show "Filled 5/7 fields (2 errors)" banner after autofill completes |
| DM draft no preview | Low | `popup.js:76-96` | 2-3 hours | Show generated DM in popup text area before clipboard copy, add "Edit" button |
| Popup retry logic too aggressive | Low | `popup.js:13-21` | 30 min | Increase retries to 5, exponential backoff 100ms → 500ms |

### Backend Gaps

| Gap | Severity | Location | Effort | Description |
|---|---|---|---|---|
| No `/api/extension/health` endpoint | High | Backend API routes | 1 hour | Add unauthenticated health check for extension connectivity testing |
| No backend tests visible | High | `services/api/tests/` | 8-16 hours | Write integration tests for all 8 `/api/extension/*` endpoints |
| No API versioning | Medium | Backend API routes | 4-8 hours | Introduce `/api/v1/extension/*` or version headers to prevent breaking changes |
| CORS config unclear | Medium | Backend deployment | 1 hour | Document actual `CORS_ALLOW_ORIGINS` value in prod, verify `chrome-extension://*` is allowed |

### Web UI / Settings Gaps

| Gap | Severity | File(s) | Effort | Description |
|---|---|---|---|---|
| Feature flag disabled in prod | **Critical** | `apps/web/Dockerfile.prod` | 10 min | Set `ARG VITE_FEATURE_COMPANION=1`, rebuild Docker image |
| No extension status page | Medium | Web UI components | 4-6 hours | Add `/settings/companion/status` showing: extension detected, last sync, API health |
| No web UI code visible | N/A | `apps/web/` workspace | N/A | Separate audit required for React components |

### Build / Infra Gaps

| Gap | Severity | Location | Effort | Description |
|---|---|---|---|---|
| No release build workflow | High | `.github/workflows/` | 2-3 hours | Create `extension-release.yml` to automate `pack.ps1` on GitHub releases |
| No CWS upload automation | Medium | CI/CD | 3-4 hours | Integrate `chrome-webstore-upload-cli` for automated CWS publishing |
| No prod smoke tests | Medium | `.github/workflows/` | 4-6 hours | Daily workflow to test extension against prod API, alert on failures |
| No rollback plan | Low | `DEPLOYMENT.md` | 1 hour | Document Chrome Web Store rollback procedure (unpublish, resubmit old version) |
| Feature flag not in Docker build | **Critical** | `apps/web/Dockerfile.prod` | 10 min | Add `ARG VITE_FEATURE_COMPANION=1` before `npm run build` step |

---

## 7. Recommendations for Dogfood v1

### Immediate (< 1 day)

1. **Enable web UI feature flag in prod** (10 min):
   ```dockerfile
   # apps/web/Dockerfile.prod (line ~31)
   ARG VITE_FEATURE_COMPANION=1
   RUN npm run build
   ```
   - Rebuild Docker image, deploy to production
   - Verify nav tab appears at `https://applylens.app`

2. **Add `/api/extension/health` endpoint** (1 hour):
   - Returns `{"status": "ok", "version": "0.1.0"}` without auth
   - Update extension popup to use this instead of `/api/profile/me` for connectivity check

3. **Document CORS config** (30 min):
   - Verify `CORS_ALLOW_ORIGINS` in production includes `chrome-extension://*`
   - Add to `DEPLOYMENT.md`

### Short-term (1-3 days)

4. **Add error handling to content script** (2-4 hours):
   - Catch fetch failures in `fetchFormAnswers()`
   - Show "API offline - retry?" message in panel
   - Add loading spinner during backend calls

5. **Create release build workflow** (2-3 hours):
   - Automate `pack.ps1` on GitHub release creation
   - Upload ZIP as release artifact

6. **Write backend integration tests** (8-16 hours):
   - Test all 8 `/api/extension/*` endpoints
   - Verify response schemas match extension expectations
   - Add to CI

### Medium-term (1-2 weeks)

7. **Add production smoke tests** (4-6 hours):
   - Daily E2E test against `https://api.applylens.app`
   - Alert on failures (Slack, email, PagerDuty)

8. **Improve DM generation UX** (2-3 hours):
   - Show DM preview in popup before clipboard copy
   - Add edit textarea + "Copy" button

9. **Add extension status page in web UI** (4-6 hours):
   - Show: extension installed (detect via API call), last sync time, API health
   - Link from `/settings/companion`

10. **Automate Chrome Web Store uploads** (3-4 hours):
    - Integrate `chrome-webstore-upload-cli`
    - Trigger on GitHub release (after build workflow)

---

## 8. Dogfood Readiness Score

| Category | Score | Max | Notes |
|---|---|---|---|
| **Extension Functionality** | 9/10 | 10 | All core features present, minor UX gaps |
| **Backend API** | 5/10 | 10 | Endpoints assumed present but not verified, no tests visible |
| **Web UI Integration** | 2/10 | 10 | Feature flag disabled, pages not visible in audit |
| **Build Process** | 7/10 | 10 | Manual build works, but no CI automation |
| **Deployment** | 3/10 | 10 | Manual process, no smoke tests, CORS unclear |
| **Documentation** | 8/10 | 10 | Excellent docs for extension, backend/web gaps |

**Overall Dogfood Readiness**: **34/60 (57%)**

**Blockers for internal dogfooding**:
1. ❌ Web UI feature flag disabled in prod (can't access settings page)
2. ❌ Backend endpoints not verified (assumed to exist based on extension code)
3. ❌ No production smoke tests (risk of silent API failures)

**Recommended path to 80%+ readiness**:
1. Enable `VITE_FEATURE_COMPANION=1` (10 min)
2. Add `/api/extension/health` endpoint (1 hour)
3. Verify all 8 backend endpoints return expected schemas (2-4 hours manual testing)
4. Add error handling to extension panel (2-4 hours)

**After these fixes**: Extension will be usable for internal team testing with known UX limitations.

---

## 9. Appendix: File Inventory

### Extension Core Files (Present)
- `manifest.json` - MV3 manifest (version 0.1.0)
- `config.js` - API base URL auto-detection
- `sw.js` - Service worker (message routing, API calls)
- `content.js` - Content script (form scanning, panel, autofill)
- `popup.js` - Extension popup (scan trigger, DM generation)
- `popup.html` - Popup UI
- `sidepanel.js/html` - Side panel UI
- `guardrails.js` - PII redaction, content sanitization

### Learning System Files (Present)
- `learning/client.js` - Event batching, sync to backend
- `learning/formMemory.js` - IndexedDB wrapper for local state
- `learning/utils.js` - Schema hashing, edit distance
- `learning.profileClient.js` - Fetch bandit profile from backend
- `learning.mergeMaps.js` - Selector map merging logic
- `src/learning/*.ts` - TypeScript versions of above (compiled to `learning/`)

### Documentation Files (Present)
- `README.md` - User-facing install guide
- `DEPLOYMENT.md` - Production deployment guide
- `SUBMISSION_CHECKLIST.md` - Chrome Web Store submission steps
- `docs/privacy.md` - Privacy policy
- `docs/CHROME_WEB_STORE_SUBMISSION.md` - CWS guidelines
- `e2e/README.companion.md` - E2E test documentation
- `PHASE_5_BACKEND_GUIDE.md` - Backend integration guide (Phase 5.x)

### Test Files (Present)
- 9 E2E spec files in `e2e/` (all @companion tests passing)
- 3 Playwright configs (standard, with-extension, panel)
- `vitest.config.ts`, `vitest.setup.ts` (unit test config)

### Missing/Unverified Files
- Backend API routes (`services/api/routers/extension.py` or similar)
- Web UI components (`apps/web/src/pages/Extension.tsx`, `apps/web/src/pages/Settings/Companion.tsx`)
- CI workflows for build/release (`extension-release.yml`, `extension-cws-upload.yml`)
- Production smoke test (`e2e/prod-companion-smoke.spec.ts`)

---

**End of Audit**
