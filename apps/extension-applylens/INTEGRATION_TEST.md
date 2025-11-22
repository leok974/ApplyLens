# Manual Integration Test - Phase 2.1 Learning Profiles

## Quick Test Instructions

### 1. Load Extension in Chrome

1. Open Chrome → `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `D:\ApplyLens\apps\extension-applylens`
5. Note the extension ID (e.g., `abcdefghij...`)

### 2. Test on Demo Form

1. Navigate to: `http://127.0.0.1:5177/demo-form.html`
2. Open DevTools (F12) → Console tab
3. Click the ApplyLens extension icon (or press Ctrl+Shift+Y if configured)
4. Click "Scan & Suggest" button

### 3. Check Integration Logs

Look for these console messages:

```
[Learning] Phase 2.1: Host: 127.0.0.1, Schema: [hash]
[Learning] Effective mapping:
  Server: 0 mappings
  Local: 0 mappings
  Merged: 0 mappings
[Learning] 🔍 Using heuristic: #full_name → full_name
[Learning] Mapping summary: 0 learned, 3 heuristic
```

**Expected behavior:**
- ✅ Extension fetches profile from `/api/extension/learning/profile`
- ✅ Profile returns 404 (no profile exists yet)
- ✅ Extension falls back to heuristics
- ✅ Autofill still works normally
- ✅ No JavaScript errors

### 4. Test with Mock Profile (Advanced)

1. Paste the content of `test-integration.js` into DevTools Console
2. Run it - it will mock the API responses
3. Look for integration success messages

### 5. Expected Network Requests

Check DevTools Network tab for:

- `GET /api/extension/learning/profile?host=127.0.0.1&schema_hash=[hash]`
  - Should return 404 (no profile) or 200 (if profile exists)
- `POST /api/extension/generate-form-answers`
  - Should return form answers as before
- `POST /api/extension/learning/sync` (after filling)
  - Should sync learning events as before

## Integration Success Criteria

### ✅ Phase 2.1 Complete When:

1. **Profile API Called**: Extension makes GET request to learning profile endpoint
2. **Graceful Fallback**: Works normally when profile returns 404
3. **No Regressions**: Existing autofill and learning sync still work
4. **Mapping Logic**: Uses server canonical_map when available
5. **Console Logs**: Shows "Phase 2.1" integration logs
6. **Tests Pass**: `npm test` still shows 15/15 passing

### ⚠️ Troubleshooting

**No profile API call?**
- Check extension is reloaded after manifest changes
- Verify imports in content.js are correct
- Check for console errors

**Profile call fails?**
- API not running: Start API server at localhost:8003
- CORS issues: Check API allows chrome-extension:// origins
- Wrong URL: Verify APPLYLENS_API_BASE in config.js

**Extension not working?**
- Check manifest.json syntax
- Reload extension in chrome://extensions
- Check for script errors in DevTools

## Next Steps After Success

1. **Test with Real Profiles**: Run aggregator to create profiles from existing events
2. **Monitor Metrics**: Check Prometheus for autofill_runs_total with profile_used=true
3. **Production Deploy**: Deploy API changes and updated extension
4. **User Feedback**: Collect feedback on improved accuracy

## Files Modified

- ✅ `content.js` - Added profile fetching and map merging
- ✅ `manifest.json` - Added new script dependencies
- ✅ `learning.profileClient.js` - ES module profile client
- ✅ `learning.mergeMaps.js` - ES module map merging
