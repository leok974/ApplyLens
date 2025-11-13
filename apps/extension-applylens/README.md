# ApplyLens Companion (MV3, zero-bundle)

- No build step. Load as unpacked.
- Talks to ApplyLens API (`/api/profile/me`, `/api/extension/*`)

## Configure

Edit `config.js`:
```js
export const APPLYLENS_API_BASE = "http://localhost:8003";
```

## Load in Chrome/Edge

1. `chrome://extensions` → Enable Developer mode
2. Load unpacked → select `apps/extension-applylens/`
3. Pin the extension. Open a job form → click "Scan form & suggest answers".

## Requires ApplyLens dev API

- `GET /api/profile/me`
- `POST /api/extension/generate-form-answers`
- `POST /api/extension/applications`
- `POST /api/extension/generate-recruiter-dm`
- `POST /api/extension/outreach`

---

## 🚀 Quick Start (Details)

### Prerequisites

1. **API Server Running**
   ```powershell
   # In D:\ApplyLens\services\api
   docker ps --filter "name=applylens-api-prod"
   # OR run local dev server:
   .\scripts\dev-api.ps1
   ```

2. **Verify API Endpoints**
   ```powershell
   curl http://localhost:8003/api/profile/me
   # Should return: {"name":"Leo Klemet",...}
   ```

### Load Extension

1. Open Chrome and navigate to `chrome://extensions`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select `D:\ApplyLens\apps\extension-applylens`
5. Extension should appear with ApplyLens icon

### Test It

1. **Open test form**: Navigate to `test/demo-form.html` in Chrome
2. **Click extension icon**: Popup should show "Connected: Leo Klemet"
3. **Fill in**:
   - Job title: "AI Engineer"
   - Company: "ApplyLens"
4. **Click "Scan form"**: Should show "6 fields detected"
5. **Click "Autofill"**: Fields should populate automatically
6. **Check API logs**: Application should be logged via `/api/extension/applications`

## 📁 Structure

```
extension-applylens/
├── manifest.json         # Chrome MV3 manifest
├── background.js         # Service worker (API calls)
├── content.js           # Page integration (form scanning)
├── lib/
│   ├── api.js          # API client functions
│   └── dom.js          # DOM utilities (scan/fill forms)
├── popup/
│   ├── popup.html      # Extension popup UI
│   ├── popup.css       # Popup styles
│   └── popup.js        # Popup logic
├── icons/              # Extension icons (16, 48, 128)
└── test/
    └── demo-form.html  # Test ATS form
```

## 🔧 Configuration

### API Settings

- **Dev mode** (default): `http://localhost:8003`
- **Prod mode**: `https://api.applylens.app`

Change in popup:
1. Click extension icon
2. Toggle "Dev mode" checkbox
3. Or edit "API Base" URL
4. Click "Save"

### Environment Variables (API)

Required for extension endpoints:
```powershell
$env:APPLYLENS_DEV="1"        # Enable dev-only endpoints
$env:ALLOW_DEV_ROUTES="1"     # Allow extension routes
```

## 🧪 Features

### 1. ATS Form Autofill

Scans page for form fields and autofills based on your profile:

- **Scan**: Detects input fields, textareas, selects
- **Generate**: API creates personalized answers
- **Fill**: Populates fields with proper events
- **Log**: Records application in database

**Supported ATS**: Greenhouse, Lever, Workday (coming soon)

### 2. LinkedIn DM Generation

Drafts recruiter outreach messages:

- **Scrape**: Extracts recruiter profile data
- **Generate**: API creates personalized DM
- **Copy**: Paste into LinkedIn message box
- **Log**: Records outreach in database

### 3. Application Tracking

Every autofill logs:
- Company name
- Job title
- Job URL
- Timestamp
- Source: "browser_extension"

## 🔒 Security

### Permissions Rationale

**`activeTab`**: Only activates when you click the extension icon. Allows reading visible form fields on the current tab to generate personalized answers. No background page scraping.

**`scripting`**: Injects a small content script to scan and fill form fields. Script only runs when you explicitly click "Scan form & suggest" - never runs automatically in the background.

**`host_permissions`**: Limited to specific domains where autofill/DM features are used:
- `https://*.greenhouse.io/*` - Greenhouse ATS forms
- `https://jobs.lever.co/*` - Lever ATS forms
- `https://*.myworkdayjobs.com/*` - Workday ATS forms
- `https://www.linkedin.com/*` - LinkedIn recruiter profiles
- `https://applylens.app/*` - ApplyLens web app
- `https://api.applylens.app/*` - ApplyLens API

All permissions follow the principle of least privilege and can be further restricted based on your usage patterns.

### Dev Mode (Current)

- ⚠️ Broad `<all_urls>` permissions (for testing)
- ⚠️ No authentication (CSRF-exempt paths)
- ⚠️ API endpoints are dev-only (`APPLYLENS_DEV=1`)

### Production (Future)

- Narrow permissions to specific ATS domains
- Add OAuth authentication
- Use production API endpoints
- Implement token refresh

## 📊 API Endpoints Used

All endpoints are in `services/api/app/routers/extension.py`:

- `GET /api/profile/me` - Get user profile
- `POST /api/extension/applications` - Log application
- `POST /api/extension/outreach` - Log recruiter outreach
- `POST /api/extension/generate-form-answers` - Generate form answers
- `POST /api/extension/generate-recruiter-dm` - Generate DM

## 🐛 Troubleshooting

### "Connect failed" in popup

**Problem**: Extension can't reach API

**Fix**:
```powershell
# Check if API is running
curl http://localhost:8003/healthz

# Check Docker container
docker ps --filter "name=applylens-api-prod"

# Or start local dev server
cd D:\ApplyLens\services\api
.\scripts\dev-api.ps1
```

### "API error: 403" or "Dev-only endpoint"

**Problem**: API dev mode not enabled

**Fix**:
```powershell
# Ensure environment variables are set
$env:APPLYLENS_DEV="1"
$env:ALLOW_DEV_ROUTES="1"

# Restart API server
```

### Autofill doesn't populate fields

**Problem**: DOM selectors not matching or events not firing

**Fix**:
1. Open browser DevTools (F12)
2. Check Console for errors
3. Try "Scan form" to see detected fields
4. Some ATS use custom form libraries (may need specific event triggers)

### Extension not loading

**Problem**: Manifest or module errors

**Fix**:
1. Go to `chrome://extensions`
2. Click "Errors" button on extension card
3. Common issues:
   - Missing `type="module"` in manifest
   - Import path errors (check `/lib/api.js` paths)
   - CORS issues (API must allow localhost)

## 🚧 Next Steps

1. **Icons**: Add actual icon images to `icons/` folder (16x16, 48x48, 128x128)
2. **Host Permissions**: Narrow to specific ATS domains:
   ```json
   "host_permissions": [
     "*://*.greenhouse.io/*",
     "*://*.lever.co/*",
     "*://*.myworkdayjobs.com/*",
     "*://*.linkedin.com/*"
   ]
   ```
3. **Options Page**: Add `/options.html` for advanced settings
4. **Authentication**: Implement OAuth flow for production
5. **Review Panel**: Add shadow DOM overlay to review answers before autofill

## 📚 Resources

- [Chrome Extension MV3 Docs](https://developer.chrome.com/docs/extensions/mv3/)
- [ApplyLens API Docs](../../services/api/docs/)
- [Extension Security Best Practices](https://developer.chrome.com/docs/extensions/mv3/security/)

## 🤝 Development

To modify:

1. Edit files in `apps/extension-applylens/`
2. Click "Reload" button in `chrome://extensions`
3. Test changes on demo form or real ATS pages
4. Check background service worker logs: `chrome://extensions` → "Inspect views: service worker"

For API changes:
1. Update endpoints in `services/api/app/routers/extension.py`
2. Restart API server
3. Test with `curl` first, then extension
