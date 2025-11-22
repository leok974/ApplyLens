# Chrome Web Store Submission - Final Checklist

**Package**: `dist/applylens-companion-20251112-174240.zip` (389.65 KB)
**Version**: 0.1.0
**Date**: November 12, 2025

## Pre-Submission Checklist

### ✅ Extension Package
- [x] Minimal permissions (activeTab, scripting, storage)
- [x] Host permissions limited to specific domains:
  - `https://*.greenhouse.io/*`
  - `https://jobs.lever.co/*`
  - `https://*.myworkdayjobs.com/*`
  - `https://www.linkedin.com/*`
  - `https://api.applylens.app/*`
- [x] Content scripts only on ATS domains
- [x] Service worker with retry logic
- [x] Privacy policy created (docs/privacy.md)
- [x] LICENSE file (MIT)
- [x] Store listing template (store-listing.json)
- [x] All tests passing (7/7)

### ⚠️ Assets Required (Create Before Upload)
- [ ] **128×128 icon** - Extension icon
- [ ] **440×280 small promo** - Store tile
- [ ] **920×680 screenshot 1** - Popup + form autofill demo
- [ ] **920×680 screenshot 2** - LinkedIn DM generation
- [ ] **920×680 screenshot 3** - Settings page with activity
- [ ] **1280×800 promotional tile** (optional but recommended)

### ✅ API Backend
- [x] Extension endpoints implemented
- [x] CORS configured for chrome-extension://*
- [x] Dev-only guard active (APPLYLENS_DEV=1)
- [x] Prometheus metrics instrumented
- [ ] **TODO**: Remove dev_only guard for production
- [ ] **TODO**: Add proper authentication

### ✅ Web App
- [x] Extension landing pages (/extension)
- [x] Companion settings page (/settings/companion)
- [x] Feature flag system (FLAGS.COMPANION)
- [x] Navigation link added
- [x] Privacy policy hosted (public/extension/privacy.html)
- [x] All tests passing (9/9)
- [ ] **TODO**: Deploy to production
- [ ] **TODO**: Enable VITE_FEATURE_COMPANION=1 in prod

### ⚠️ Infrastructure
- [ ] **CORS in production**: Add to API env vars:
  ```bash
  CORS_ALLOW_ORIGINS=https://applylens.app,https://www.applylens.app,chrome-extension://*
  ```
- [ ] **Cloudflare WAF**: Rate limit /api/extension/* to 60 req/min per IP
- [ ] **CI artifact retention**: Update .github/workflows/extension-e2e.yml

## Store Submission Steps

### 1. Upload Package
1. Go to [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole/)
2. Click "New Item"
3. Upload `dist/applylens-companion-20251112-174240.zip`
4. Wait for automated checks

### 2. Store Listing
**Name** (45 char max):
```
ApplyLens Companion
```

**Summary** (132 char max):
```
Autofill ATS forms and draft recruiter DMs using your ApplyLens profile.
```

**Description**:
```
ApplyLens Companion helps you move faster on job applications:

• Scan job application forms (Greenhouse, Lever, Workday) and suggest concise, relevant answers using your ApplyLens profile
• Draft tailored recruiter DMs for LinkedIn
• (Optional) Log applications and outreach to your ApplyLens tracker

Privacy-first:
• Only captures metadata you choose to log (company, role, job URL)
• No background browsing history, no ad tracking
• All communication is HTTPS; you can delete logs anytime from ApplyLens

Get started:
1) Install the extension
2) Open a job application page → click the extension → "Scan form & suggest"
3) On LinkedIn profiles → "Draft recruiter DM" → copy/paste

Support: leoklemet.pa@gmail.com
```

**Category**: Productivity

**Language**: English

### 3. Screenshots & Assets
Upload these to Chrome Developer Dashboard:

1. **Icon (128×128)**: `icons/icon128.png`
2. **Small promo tile (440×280)**: Create from brand assets
3. **Screenshot 1**: Popup + form autofill demo
4. **Screenshot 2**: LinkedIn DM generation
5. **Screenshot 3**: Settings page with activity tracking

### 4. Privacy Practices

**Privacy Policy URL**:
```
https://applylens.app/extension/privacy
```

**Single Purpose**:
```
ApplyLens Companion autofills job application forms and drafts personalized recruiter messages using your ApplyLens profile data.
```

**Permissions Justification**:

- **activeTab**: Only when you click the extension, reads visible fields to generate answers.
- **scripting**: Injects content script on the current tab to scan fields and fill suggestions.
- **storage**: Stores minimal state (API endpoint preference, last sync time).

**Host Permissions**:
- `https://*.greenhouse.io/*` - Greenhouse ATS forms
- `https://jobs.lever.co/*` - Lever ATS forms
- `https://*.myworkdayjobs.com/*` - Workday ATS forms
- `https://www.linkedin.com/*` - LinkedIn recruiter profiles
- `https://api.applylens.app/*` - ApplyLens API

**Data Collection**:
- [x] Collects data: YES
- Data types: User activity (company, role, job URL, timestamps)
- [x] Shared with third parties: NO
- [x] Sold to third parties: NO
- [x] Encrypted in transit: YES (HTTPS only)

**Data Deletion**:
```
You can delete logged application/outreach entries from ApplyLens at any time; this removes them from our systems.
```

### 5. Submit for Review
1. Review all information
2. Click "Submit for review"
3. Wait 1-3 business days for approval

## Post-Submission

### If Approved
1. **Note Extension ID**: `chrome-extension://<YOUR_ID>`
2. **Update manifest host_permissions** (optional, more secure):
   ```json
   "host_permissions": [
     "https://*.greenhouse.io/*",
     "https://jobs.lever.co/*",
     "https://*.myworkdayjobs.com/*",
     "https://www.linkedin.com/*",
     "https://api.applylens.app/*"
   ]
   ```
3. **Update CORS in API** to use specific extension ID:
   ```bash
   CORS_ALLOW_ORIGINS=https://applylens.app,chrome-extension://<YOUR_ID>
   ```
4. **Update web app** with real Chrome Web Store URL:
   - Edit `apps/web/src/pages/extension/ExtensionLanding.tsx`
   - Replace `<YOUR_ID>` with actual extension ID
5. **Tag release**:
   ```bash
   cd d:\ApplyLens
   git tag ext-v0.1.0
   git push origin ext-v0.1.0
   ```

### If Rejected
Common reasons and fixes:
1. **Insufficient privacy disclosure** → Ensure privacy.html is complete and hosted
2. **Overly broad permissions** → Already fixed (no more <all_urls>)
3. **Missing screenshots** → Create the 3 required screenshots
4. **Unclear purpose** → Update description to be more specific

## Production Deployment

### API Updates
```bash
# Remove dev-only guard
# In services/api/app/routers/extension.py, remove or comment out:
# dependencies=[Depends(dev_only)]

# Add authentication
# Replace with proper OAuth or API key validation

# Update CORS
export CORS_ALLOW_ORIGINS="https://applylens.app,https://www.applylens.app,chrome-extension://<YOUR_ID>"

# Restart API
docker restart applylens-api-prod
```

### Web App Updates
```bash
# Enable feature flag in production
# In apps/web/.env.production (or deployment config):
VITE_FEATURE_COMPANION=1

# Deploy
npm run build
# Upload to hosting/CDN
```

### Monitoring
After launch, monitor:
- Prometheus metrics: `applylens_extension_*`
- Error rates: `http_request_duration_seconds{route="/api/extension/*"}`
- User feedback via leoklemet.pa@gmail.com

## Final Smoke Tests

Before submitting to Chrome Web Store, run these tests:

```bash
# 1. Extension E2E tests
cd d:\ApplyLens\apps\extension-applylens
npm test  # Should be 7/7 passing

# 2. Web app tests
cd d:\ApplyLens\apps\web
npx playwright test --config playwright.companion.config.ts
# Should be 9/9 passing

# 3. API tests
cd d:\ApplyLens\services\api
pytest tests/test_extension_endpoints.py -v
# Should be 2/2 passing

# 4. Manual test
# - Load extension in Chrome
# - Click popup → verify profile loads
# - Go to Greenhouse job page → click "Scan form"
# - Verify fields populate
# - Check /settings/companion → verify activity logged
```

## Contact & Support

**Developer**: Leo Klemet
**Email**: leoklemet.pa@gmail.com
**Repository**: https://github.com/leok974/ApplyLens
**Branch**: thread-viewer-v1

## Version History

- **v0.1.0** (2025-11-12) - Initial release
  - Form autofill for Greenhouse, Lever, Workday
  - LinkedIn DM generation
  - Optional activity logging
  - Privacy-first design
