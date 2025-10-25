# Quick Test Guide: Search Filter Interactivity

## 🎯 Quick Manual Test (2 minutes)

### Prerequisites
- Production site: https://applylens.app/web/search?q=Interview
- OR Local: http://localhost:5175/search?q=Interview

### Test Steps

1. **Label Filters**
   ```
   ✓ Click "Interview" chip
   ✓ URL should change to: ...?q=Interview&labels=interview
   ✓ Results should refresh
   ✓ Click again to deselect
   ```

2. **Category Filters**
   ```
   ✓ Click "ats" button
   ✓ URL should change to: ...&cat=ats
   ✓ Button should highlight
   ✓ Results should filter to ATS emails
   ```

3. **Reply Status**
   ```
   ✓ Click "Replied" chip
   ✓ URL should change to: ...&replied=true
   ✓ Only replied emails show
   ```

4. **Date Range**
   ```
   ✓ Set "From" date: 2025-01-01
   ✓ Set "To" date: 2025-12-31
   ✓ URL should update with: ...&date_from=2025-01-01&date_to=2025-12-31
   ✓ Results within date range only
   ```

5. **Security Filters**
   ```
   ✓ Click "High Risk" toggle
   ✓ URL should change to: ...&risk_min=80
   ✓ Only high-risk emails show
   ```

6. **Clear All**
   ```
   ✓ Apply multiple filters
   ✓ Click "Clear all filters"
   ✓ All filters reset
   ✓ URL should only have: ?q=Interview
   ```

7. **Sort Order**
   ```
   ✓ Change sort dropdown to "Newest"
   ✓ URL should update: ...&sort=received_desc
   ✓ Results re-order by date
   ```

### Expected Behavior
- ✅ All buttons respond immediately to clicks
- ✅ URL updates reflect filter changes
- ✅ Results refresh after ~150ms debounce
- ✅ No lag or unresponsive buttons
- ✅ Filters work with keyboard (Tab + Enter)

### Common Issues (Now Fixed)
- ❌ ~~Buttons don't respond to clicks~~ → Fixed with `type="button"`
- ❌ ~~Form submits when clicking filters~~ → Fixed with explicit button types
- ❌ ~~Transparent overlay blocks clicks~~ → Fixed with `pointer-events-auto`
- ❌ ~~Filters disabled when paused~~ → Never was an issue (no paused state on Search)

## 🔍 Debug Script Test

Open DevTools Console (F12) and paste:

```javascript
// Check for blocking overlays
(() => {
  const el = document.elementFromPoint(
    Math.round(window.innerWidth * 0.25),
    Math.round(window.innerHeight * 0.35)
  );

  console.log("🔍 Top element under cursor:", el);

  if (!el) {
    console.warn("⚠️ No element found");
    return;
  }

  const cs = getComputedStyle(el);

  console.table({
    tag: el.tagName,
    zIndex: cs.zIndex,
    opacity: cs.opacity,
    pointerEvents: cs.pointerEvents,
    position: cs.position,
  });

  if (cs.pointerEvents === "auto" && parseFloat(cs.opacity) < 0.1) {
    console.error("🚨 STEALTH OVERLAY DETECTED!");
  } else {
    console.info("✅ No blocking overlays");
  }
})();
```

**Expected Output**:
```
✅ No blocking overlays
ℹ️ Element is interactive (pointer-events: auto)
```

## 🧪 Automated E2E Test

Run the comprehensive test suite:

```powershell
# Full test suite
cd apps/web
npm run test:e2e -- search.interactions.spec.ts

# With browser (watch tests run)
npm run test:e2e:headed -- search.interactions.spec.ts

# Specific test
npm run test:e2e -- search.interactions.spec.ts -g "label filters"
```

**Expected**: All tests pass ✅

**Test Coverage**:
- ✓ Label filter clicks update URL
- ✓ Category filter interactions
- ✓ Replied filter chips
- ✓ Date range controls
- ✓ Security filters
- ✓ Clear all filters
- ✓ Sort control
- ✓ No stealth overlays
- ✓ No disabled fieldsets

## 🐛 Troubleshooting

### Issue: Filters still not clickable

**Check 1: Clear browser cache**
```
Ctrl+Shift+R (hard refresh)
OR
DevTools → Network → Disable cache
```

**Check 2: Verify container version**
```powershell
docker ps --filter "name=applylens-web-prod"
# Should show: Up X seconds (healthy)

docker exec applylens-web-prod cat /usr/share/nginx/html/index.html | head -n 1
# Should show recent build timestamp
```

**Check 3: Check console for errors**
```
F12 → Console
Look for:
- Network errors (red)
- JavaScript errors
- CORS issues
```

### Issue: URL doesn't update

**Check**: React Router is working
```javascript
// In Console
console.log(window.location.search)
// Should show: ?q=Interview&labels=...
```

**Check**: useSearchParams hook
```javascript
// Look for searchParams in React DevTools
// Should see params object updating
```

### Issue: Results don't refresh

**Check**: Network tab shows API calls
```
F12 → Network → Filter: Fetch/XHR
After clicking filter:
- Should see POST/GET to /api/search/
- With query params in payload
```

**Check**: API endpoint is up
```powershell
curl http://localhost:8003/health
# Should return: {"status": "healthy"}
```

## 📊 Success Criteria

✅ **All tests pass**
- Manual test: 7/7 checks pass
- Debug script: No blocking overlays
- E2E tests: 100% pass rate

✅ **Performance**
- Filter click → URL update: < 50ms
- URL update → API call: ~150ms (debounced)
- API call → results render: < 500ms
- Total interaction time: < 700ms

✅ **Accessibility**
- Keyboard navigation works (Tab + Enter)
- Screen reader announces filter changes
- Focus visible on active element
- No keyboard traps

✅ **Cross-browser**
- Chrome/Edge ✓
- Firefox ✓
- Safari ✓
- Mobile browsers ✓

## 🚀 Production Verification

After deploying to production:

1. **Smoke Test** (1 min)
   - Visit: https://applylens.app/web/search?q=Interview
   - Click 2-3 different filters
   - Verify URL updates and results change

2. **Analytics Check** (optional)
   ```javascript
   // If you have analytics:
   // Track filter click events
   gtag('event', 'filter_click', {
     filter_type: 'label',
     filter_value: 'interview'
   });
   ```

3. **Error Monitoring**
   - Check Sentry/error logs for:
     - TypeError: Cannot read properties
     - Network errors on search API
     - Unhandled promise rejections

## 📝 Commit & Deploy

```bash
# Verify changes
git status

# Stage changes
git add apps/web/src/components/
git add apps/web/src/pages/Search.tsx
git add apps/web/tests/search.interactions.spec.ts
git add apps/web/public/debug-overlay.js
git add SEARCH_FILTER_FIXES.md
git add QUICK_TEST_GUIDE.md

# Commit
git commit -m "fix(search): restore filter interactivity

- Add pointer-events-auto to ActionsTray backdrop when visible
- Standardize type=\"button\" on all filter buttons
- Add diagnostics script and E2E tests
- Verify URL param → fetch flow working correctly"

# Push
git push origin demo

# Deploy (if using CD pipeline)
# OR rebuild container manually:
docker build -f apps/web/Dockerfile.prod -t leoklemet/applylens-web:latest apps/web/
docker-compose -f docker-compose.prod.yml up -d --force-recreate web
```

## ✅ Done!

Filters should now be fully interactive. If you still experience issues, check:
1. Browser cache cleared
2. Container version updated
3. API backend is healthy
4. No JavaScript errors in console

For help: Check `SEARCH_FILTER_FIXES.md` for detailed technical docs.
