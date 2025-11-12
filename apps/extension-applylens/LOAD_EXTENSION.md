# 🚀 Load Extension - Quick Start

## Extension is ready! Follow these steps:

### 1️⃣ Open Chrome Extensions Page
- Open Chrome browser
- Go to: `chrome://extensions`
- Or: Menu → Extensions → Manage Extensions

### 2️⃣ Enable Developer Mode
- Toggle "Developer mode" switch (top right corner)

### 3️⃣ Load Extension
- Click "Load unpacked" button
- Navigate to: `D:\ApplyLens\apps\extension-applylens`
- Click "Select Folder"

### 4️⃣ Verify Installation
- ✅ You should see "ApplyLens Browser Companion (Dev)" in the list
- ✅ Version 0.1.0
- ✅ Green icons indicating it's active

### 5️⃣ Test It!

**Option A: Test with Demo Form**
1. Open new tab in Chrome
2. Press `Ctrl+O` or `File → Open File`
3. Navigate to: `D:\ApplyLens\apps\extension-applylens\test\demo-form.html`
4. Click the ApplyLens extension icon (top right)
5. Should show: "Connected: Leo Klemet"
6. Fill in:
   - Job title: "AI Engineer"
   - Company: "Acme Corp"
7. Click "Scan form" → Should show "6 fields detected"
8. Click "Autofill" → Fields should populate!

**Option B: Test on Real ATS**
1. Open any job application page (Greenhouse, Lever, etc.)
2. Click extension icon
3. Enter job details and try autofill

### 📊 API Status
- **Server**: Docker container `applylens-api-prod`
- **Port**: 8003
- **Health**: ✅ Running (verified `/api/profile/me`)
- **Mode**: Production (use dev mode in extension settings)

### ⚙️ Extension Settings

To use with local Docker API:
1. Click extension icon
2. Uncheck "Dev mode"
3. Set API Base: `http://localhost:8003`
4. Click "Save"

### 🐛 Troubleshooting

**Extension doesn't appear:**
- Check for errors: Click "Errors" button on extension card
- Common fix: Refresh the extensions page

**"Connect failed" message:**
- Verify API is running: `docker ps --filter "name=applylens-api-prod"`
- Test endpoint: `curl http://localhost:8003/api/profile/me`

**Autofill doesn't work:**
- Open DevTools (F12) → Console tab
- Look for JavaScript errors
- Try "Scan form" first to see detected fields

### 📁 Files Created
```
extension-applylens/
├── manifest.json          ✅ Chrome MV3 config
├── background.js          ✅ Service worker
├── content.js            ✅ Page integration
├── lib/
│   ├── api.js           ✅ API client
│   └── dom.js           ✅ Form utilities
├── popup/
│   ├── popup.html       ✅ UI
│   ├── popup.css        ✅ Styles
│   └── popup.js         ✅ Logic
├── icons/
│   ├── icon16.png       ✅ From apps/web
│   ├── icon48.png       ✅ From apps/web
│   └── icon128.png      ✅ From apps/web (512→128)
└── test/
    └── demo-form.html   ✅ Test page
```

### 🎯 Next Steps After Loading

1. **Test Demo Form**: Verify autofill works
2. **Try Real ATS**: Test on Greenhouse or Lever
3. **Check Logs**: Background service worker logs
4. **LinkedIn DM**: Test DM generation on LinkedIn profiles
5. **View Metrics**: Check database for logged applications

---

**Ready to load? Go to `chrome://extensions` and follow steps above!** 🎉
