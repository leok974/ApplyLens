# Production Deployment Guide

## 🚀 Quick Start

### 1. Build Production Package
```powershell
cd apps/extension-applylens
.\pack.ps1
```

This creates: `dist/applylens-companion-YYYYMMDD-HHmmss.zip`

### 2. Upload to Chrome Web Store
1. Go to [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
2. Click "New Item"
3. Upload the generated ZIP file
4. Fill in store listing details
5. Submit for review

### 3. Production API Configuration

The extension automatically detects the environment:
- **Development**: Uses `http://localhost:8003` (file:// or localhost)
- **Production**: Uses `https://api.applylens.app` (chrome-extension://)

No manual config changes needed!

## 🔧 Manual Configuration Override

If you need to force a specific API endpoint:

### Option A: Edit config.js directly
```javascript
export const APPLYLENS_API_BASE = "https://api.applylens.app";
```

### Option B: Create config variants
1. Create `config.dev.js` and `config.prod.js`
2. In `pack.ps1`, add: `Copy-Item config.prod.js config.js -Force`
3. Run `.\pack.ps1`

## 🌐 Server CORS Configuration

### Already Configured! ✅

The API server (`services/api/app/main.py`) supports extension requests:

**Dev Mode** (`APPLYLENS_DEV=1`):
- Allows `chrome-extension://*` via regex
- Allows all `localhost:*` ports
- Allows `127.0.0.1:*`

**Production Mode**:
- Set `CORS_ALLOW_ORIGINS` environment variable:
  ```bash
  CORS_ALLOW_ORIGINS=https://applylens.app,https://api.applylens.app
  ```

**Note**: Chrome extensions don't send cookies by default, so `allow_credentials` is safe.

## 🧪 Testing Production Build

### Test Locally with Production API
1. Build: `.\pack.ps1`
2. Extract ZIP to a test folder
3. Load unpacked extension in Chrome
4. Extension will use `https://api.applylens.app` automatically

### Test with Local API
1. Don't pack - use source files directly
2. Load unpacked from `apps/extension-applylens/`
3. Extension will use `http://localhost:8003`

## 📦 Package Contents

The production ZIP includes:
- `manifest.json` - Extension metadata
- `config.js` - Auto-detecting API config
- `sw.js` - Service worker (background)
- `content.js` - Content script (page injection)
- `popup.html/js` - Extension popup UI
- `sidepanel.html/js` - Side panel UI
- `icons/` - Extension icons (16, 48, 128)
- `README.md` - User documentation

## 🔒 Security Notes

### API Authentication
Currently, the extension makes unauthenticated requests. For production:

1. **Add OAuth token storage** in service worker:
   ```javascript
   chrome.storage.local.set({ token: "..." });
   ```

2. **Include token in requests**:
   ```javascript
   headers: {
     "content-type": "application/json",
     "Authorization": `Bearer ${token}`
   }
   ```

3. **Update API endpoints** to verify tokens

### CSRF Protection
Extension requests bypass CSRF checks (different origin). Ensure:
- API validates request origin
- Sensitive endpoints require authentication
- Rate limiting is enabled (already configured)

## 🚦 CI/CD Pipeline

The workflow (`.github/workflows/extension-e2e.yml`) automatically:

1. ✅ Runs E2E tests with real Chrome extension
2. ✅ Builds production ZIP
3. ✅ Uploads artifact for manual Chrome Store submission

### Manual Publishing
GitHub Actions can't auto-publish to Chrome Web Store (requires manual review).
Download the artifact and upload manually.

### Automated Publishing (Advanced)
Use [chrome-webstore-upload](https://github.com/fregante/chrome-webstore-upload-cli):
```yaml
- run: npx chrome-webstore-upload-cli upload --source dist/*.zip
  env:
    EXTENSION_ID: ${{ secrets.CHROME_EXTENSION_ID }}
    CLIENT_ID: ${{ secrets.CHROME_CLIENT_ID }}
    CLIENT_SECRET: ${{ secrets.CHROME_CLIENT_SECRET }}
    REFRESH_TOKEN: ${{ secrets.CHROME_REFRESH_TOKEN }}
```

## 🐛 Troubleshooting

### Extension shows "Failed to fetch profile"
- Check API endpoint in browser DevTools (Network tab)
- Verify CORS headers in response
- Check API server logs

### "chrome.runtime.sendMessage is not defined"
- Content script running outside extension context
- Check manifest `content_scripts.matches` includes target URL

### Form fields not filling
- Open DevTools Console on target page
- Check for content script errors
- Verify field selectors match page structure

## 📊 Monitoring

### Extension Metrics (Future)
Track usage via API endpoints:
- `/api/extension/applications` - Application tracking
- `/api/extension/outreach` - Outreach logging

### API Metrics (Existing)
Grafana dashboards already configured:
- `applylens_http_requests_total{path="/api/extension/*"}`
- `rate(applylens_http_requests_total[5m])`

## 🎯 Version Management

Update version in `manifest.json`:
```json
{
  "version": "0.2.0",
  "version_name": "0.2.0 Beta"
}
```

Chrome requires version bumps for every update.

## 📝 Changelog

### v0.1.0 (Initial Release)
- Auto-fill ATS forms from ApplyLens profile
- Generate recruiter DMs
- Track applications and outreach
- Zero-bundle architecture (no build step)
- Auto-detecting dev/prod API endpoints
