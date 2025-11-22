# Wiring Learning Profiles into Extension Content Script

## Overview

This guide shows how to integrate the learning profile system into your extension's `content.js` to use server-aggregated canonical mappings for autofill.

## Prerequisites

You should already have:
- ✅ `learning.client.js` - Learning sync client
- ✅ `learning.formMemory.js` - Local form memory storage
- ✅ `learning.profileClient.js` - NEW: Server profile fetching
- ✅ `learning.mergeMaps.js` - NEW: Map merge logic

## Step 1: Find Your Autofill Entry Point

Look in `content.js` for one of these patterns:

### Pattern A: Message Handler
```javascript
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "SCAN_AND_SUGGEST") {
    performScanAndAutofill();
  }
});
```

### Pattern B: Direct Function
```javascript
function scanAndAutofill() {
  // Your existing scan logic
}
```

### Pattern C: Click Handler
```javascript
document.getElementById("suggest-btn").addEventListener("click", () => {
  runAutofillFlow();
});
```

## Step 2: Add Imports at Top of content.js

```javascript
// Existing imports
// ... (keep your current imports)

// NEW: Add these imports for Phase 2.1
// If you're using modules, adjust paths as needed
```

If `content.js` doesn't use modules, you can load the scripts in your `manifest.json`:

```json
{
  "content_scripts": [{
    "matches": ["<all_urls>"],
    "js": [
      "learning.formMemory.js",
      "learning.profileClient.js",
      "learning.mergeMaps.js",
      "learning.client.js",
      "content.js"
    ]
  }]
}
```

## Step 3: Compute Schema Hash

If you don't already have `computeSchemaHash`, add this helper:

```javascript
/**
 * Compute a simple hash of the form schema for caching.
 * Based on input names/ids.
 */
function computeSchemaHash(doc) {
  const inputs = Array.from(doc.querySelectorAll("input, textarea, select"));
  const signature = inputs
    .map(el => `${el.name || el.id || el.tagName}`)
    .sort()
    .join("|");

  // Simple hash function
  let hash = 0;
  for (let i = 0; i < signature.length; i++) {
    hash = ((hash << 5) - hash) + signature.charCodeAt(i);
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(16);
}
```

## Step 4: Modify Your Autofill Function

Find the function that performs the scan/autofill. It probably looks like:

```javascript
async function scanAndAutofill() {
  // Get all form fields
  const fields = document.querySelectorAll("input, textarea, select");

  // For each field, determine semantic mapping
  for (const field of fields) {
    const selector = buildSelector(field); // Your existing logic

    // OLD: Direct heuristic mapping
    const semantic = inferSemanticFromHeuristics(field);
    mapFieldToSemantic(field, semantic);
  }
}
```

**Replace it with this:**

```javascript
async function scanAndAutofill() {
  // 1. Compute host and schema hash
  const host = window.location.host;
  const schemaHash = computeSchemaHash(document);

  // 2. Load FormMemory and fetch server profile in parallel
  const [memory, profile] = await Promise.all([
    loadFormMemory(host, schemaHash),    // From learning.formMemory.js
    fetchLearningProfile(host, schemaHash) // From learning.profileClient.js
  ]);

  // 3. Merge server canonical map with local memory
  const serverMap = profile?.canonicalMap || {};
  const localMap = memory?.selectorMap || {};
  const effectiveMap = mergeSelectorMaps(serverMap, localMap); // From learning.mergeMaps.js

  console.log("📊 Effective selector map:", effectiveMap);
  console.log("  Server provided:", Object.keys(serverMap).length, "mappings");
  console.log("  Local memory:", Object.keys(localMap).length, "mappings");
  console.log("  Merged total:", Object.keys(effectiveMap).length, "mappings");

  // 4. Get all form fields
  const fields = document.querySelectorAll("input, textarea, select");

  // 5. For each field, use effective map or fall back to heuristics
  for (const field of fields) {
    const selector = buildSelector(field); // Your existing logic

    let semantic;

    // Check merged map first
    if (effectiveMap[selector]) {
      semantic = effectiveMap[selector];
      console.log(`✅ Using learned mapping: ${selector} → ${semantic}`);
    } else {
      // Fall back to heuristics
      semantic = inferSemanticFromHeuristics(field);
      console.log(`🔍 Using heuristic: ${selector} → ${semantic}`);
    }

    // Apply the mapping
    mapFieldToSemantic(field, semantic);
  }

  // 6. (Optional) Use style hint from profile
  if (profile?.styleHint && profile.styleHint.confidence > 0.7) {
    console.log(`💡 Recommended style: ${profile.styleHint.genStyleId} (${(profile.styleHint.confidence * 100).toFixed(0)}% confidence)`);
    // You can use this to set a preferred generation style
  }

  // Keep your existing learning sync behavior unchanged
  // (edit stats tracking, queueLearningEvent, flushLearningEvents)
}
```

## Step 5: Update buildSelector Helper (If Needed)

Make sure your `buildSelector` function returns consistent CSS selectors. Example:

```javascript
function buildSelector(element) {
  // Try name attribute first
  if (element.name) {
    return `input[name='${element.name}']`;
  }

  // Try id attribute
  if (element.id) {
    return `#${element.id}`;
  }

  // Fall back to tag + type
  const tag = element.tagName.toLowerCase();
  const type = element.type || "";
  return type ? `${tag}[type='${type}']` : tag;
}
```

## Step 6: Keep Existing Learning Sync

Your existing learning sync logic should remain unchanged:

```javascript
// After autofill completes, sync events to backend
await flushLearningEvents();
```

This sends the `AutofillEvent` data to the backend, which the aggregator uses to compute canonical maps for future users.

## Complete Example

Here's a full example integrating everything:

```javascript
// content.js - Complete integration example

// Assume learning.formMemory.js, learning.profileClient.js,
// learning.mergeMaps.js are loaded via manifest.json

/**
 * Compute form schema hash
 */
function computeSchemaHash(doc) {
  const inputs = Array.from(doc.querySelectorAll("input, textarea, select"));
  const signature = inputs
    .map(el => `${el.name || el.id || el.tagName}`)
    .sort()
    .join("|");

  let hash = 0;
  for (let i = 0; i < signature.length; i++) {
    hash = ((hash << 5) - hash) + signature.charCodeAt(i);
    hash = hash & hash;
  }
  return Math.abs(hash).toString(16);
}

/**
 * Build consistent CSS selector for element
 */
function buildSelector(element) {
  if (element.name) return `input[name='${element.name}']`;
  if (element.id) return `#${element.id}`;
  return element.tagName.toLowerCase();
}

/**
 * Infer semantic meaning from field attributes (fallback)
 */
function inferSemanticFromHeuristics(field) {
  const name = (field.name || "").toLowerCase();
  const id = (field.id || "").toLowerCase();
  const placeholder = (field.placeholder || "").toLowerCase();

  if (/first.*name|fname/.test(name + id + placeholder)) return "first_name";
  if (/last.*name|lname/.test(name + id + placeholder)) return "last_name";
  if (/email/.test(name + id + placeholder)) return "email";
  if (/phone|tel/.test(name + id + placeholder)) return "phone";

  return "unknown";
}

/**
 * Apply semantic mapping to field
 */
function mapFieldToSemantic(field, semantic) {
  // Store semantic in data attribute for later use
  field.dataset.semantic = semantic;

  // You might also fill the field here if you have profile data
  // Example: if (profileData[semantic]) field.value = profileData[semantic];
}

/**
 * Main autofill function - PHASE 2.1 INTEGRATED
 */
async function scanAndAutofill() {
  console.log("🚀 Starting scan and autofill (Phase 2.1)...");

  // 1. Compute host and schema hash
  const host = window.location.host;
  const schemaHash = computeSchemaHash(document);

  console.log(`📍 Host: ${host}, Schema: ${schemaHash}`);

  // 2. Load FormMemory and fetch server profile in parallel
  const [memory, profile] = await Promise.all([
    loadFormMemory(host, schemaHash),
    fetchLearningProfile(host, schemaHash)
  ]);

  // 3. Merge server canonical map with local memory
  const serverMap = profile?.canonicalMap || {};
  const localMap = memory?.selectorMap || {};
  const effectiveMap = mergeSelectorMaps(serverMap, localMap);

  console.log("📊 Effective mapping:");
  console.log("  Server:", Object.keys(serverMap).length, "mappings");
  console.log("  Local:", Object.keys(localMap).length, "mappings");
  console.log("  Merged:", Object.keys(effectiveMap).length, "mappings");

  // 4. Get all form fields
  const fields = document.querySelectorAll("input, textarea, select");
  console.log(`🔍 Found ${fields.length} form fields`);

  // 5. Map each field using effectiveMap or heuristics
  let learnedCount = 0;
  let heuristicCount = 0;

  for (const field of fields) {
    const selector = buildSelector(field);
    let semantic;

    if (effectiveMap[selector]) {
      semantic = effectiveMap[selector];
      learnedCount++;
    } else {
      semantic = inferSemanticFromHeuristics(field);
      heuristicCount++;
    }

    mapFieldToSemantic(field, semantic);
  }

  console.log(`✅ Mapped ${learnedCount} via learning, ${heuristicCount} via heuristics`);

  // 6. (Optional) Log style hint
  if (profile?.styleHint) {
    console.log(`💡 Style: ${profile.styleHint.genStyleId} (${(profile.styleHint.confidence * 100).toFixed(0)}%)`);
  }

  // Keep existing sync behavior
  // (your existing code for queueLearningEvent, etc.)
}

// Listen for scan trigger
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "SCAN_AND_SUGGEST") {
    scanAndAutofill()
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Async response
  }
});

console.log("📦 ApplyLens Companion content script loaded (Phase 2.1)");
```

## Testing

### 1. Load Extension in Chrome

```
1. Open Chrome → chrome://extensions
2. Enable Developer mode
3. Click "Load unpacked"
4. Select D:\ApplyLens\apps\extension-applylens
```

### 2. Test on a Form

```
1. Navigate to any form (e.g., http://localhost:4173/test/demo-form.html)
2. Open DevTools Console
3. Trigger autofill (click extension icon or send message)
4. Look for console logs:
   - "Starting scan and autofill (Phase 2.1)..."
   - "Effective mapping: ..."
   - "Mapped X via learning, Y via heuristics"
```

### 3. Verify Profile Fetching

Check Network tab in DevTools:
- Should see: `GET /api/extension/learning/profile?host=...&schema_hash=...`
- Response should have `canonical_map` and `style_hint`

### 4. Verify Fallback

If profile doesn't exist (404):
- Should see: "Server: 0 mappings" (profile is null)
- Autofill should still work via heuristics
- No errors in console

## Troubleshooting

### Profile not fetching
- Check API is running: `http://localhost:8003/api/extension/learning/profile?host=test&schema_hash=test`
- Check CORS: Should allow `chrome-extension://` origins
- Check DevTools Network tab for request

### Wrong mappings used
- Check merge logic: `console.log(serverMap, localMap, effectiveMap)`
- Verify local map isn't stale: Clear extension storage
- Verify server profile is up to date: Run aggregator

### Extension not loading
- Check manifest.json has correct script order
- Check for syntax errors in console
- Try reloading extension

## Next Steps

1. **Test with real forms** - Navigate to job application forms and verify mappings
2. **Run aggregator** - Populate profiles with existing event data
3. **Monitor metrics** - Check Prometheus for `applylens_autofill_runs_total`
4. **Iterate** - Collect feedback on mapping accuracy

## Related Files

- Backend: `services/api/app/routers/extension_learning.py`
- Backend: `services/api/app/autofill_aggregator.py`
- Extension: `apps/extension-applylens/learning.client.js`
- Extension: `apps/extension-applylens/learning.formMemory.js`
- Tests: `apps/extension-applylens/e2e/learning-profile.spec.ts`
