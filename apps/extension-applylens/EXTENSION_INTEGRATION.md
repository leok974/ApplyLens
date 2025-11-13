# Phase 2.1: Extension Integration Guide

## Overview

This guide shows how to integrate the learning profile client into your extension's content script to use server-aggregated canonical mappings for autofill.

## Files Created

### 1. Type Definitions
- **File:** `src/learning/types.ts` (extended)
- **Added:** `LearningProfile` interface

### 2. Profile Client
- **File:** `src/learning/profileClient.ts` (new)
- **Exports:** `fetchLearningProfile(host, schemaHash)`

### 3. Merge Helper
- **File:** `src/learning/mergeMaps.ts` (new)
- **Exports:** `mergeSelectorMaps(serverMap, localMap)`

### 4. Tests
- **File:** `tests/mergeMaps.test.ts` (new)
- **File:** `tests/profileClient.test.ts` (new)
- **File:** `e2e/learning-profile.spec.ts` (new)

## Integration Steps

### Step 1: Import Required Modules

In your content script (e.g., `src/content.ts` or `src/content/scan.ts`):

```typescript
import { loadFormMemory } from "./learning/formMemory";
import { fetchLearningProfile } from "./learning/profileClient";
import { mergeSelectorMaps } from "./learning/mergeMaps";
import type { SelectorMap } from "./learning/types";
```

### Step 2: Update scanAndSuggest Function

```typescript
async function scanAndSuggest() {
  const host = window.location.host;
  const schemaHash = computeSchemaHash(document); // Your existing logic

  // 1. Load local memory (Phase 1.5)
  const memory = await loadFormMemory(host, schemaHash);

  // 2. Try to fetch server profile (Phase 2.1)
  const profile = await fetchLearningProfile(host, schemaHash);

  // 3. Build effective selector map
  const serverMap: SelectorMap = profile?.canonicalMap ?? {};
  const localMap: SelectorMap = memory?.selectorMap ?? {};
  const effectiveSelectorMap = mergeSelectorMaps(serverMap, localMap);

  // 4. Use effectiveSelectorMap when building field mappings
  const fields = document.querySelectorAll("input, textarea, select");

  for (const field of fields) {
    const selector = buildSelector(field); // Your existing logic

    // Check merged map first
    if (effectiveSelectorMap[selector]) {
      const semantic = effectiveSelectorMap[selector];
      // Use this semantic mapping
      mapFieldToSemantic(field, semantic);
    } else {
      // Fall back to heuristics
      const semantic = inferSemanticFromHeuristics(field);
      mapFieldToSemantic(field, semantic);
    }
  }

  // 5. (Optional) Use style hint from profile
  if (profile?.styleHint && profile.styleHint.confidence > 0.7) {
    console.log(`Using recommended style: ${profile.styleHint.genStyleId}`);
    // Apply style preference to content generation
  }

  // ... rest of your existing scan logic ...
}
```

### Step 3: Fallback Behavior

The integration gracefully handles missing profiles:

```typescript
// If fetchLearningProfile returns null (404, network error, etc.)
// → serverMap = {}
// → mergeSelectorMaps({}, localMap) = localMap
// → Behaves exactly like Phase 1.5 (FormMemory + heuristics)

// This ensures backward compatibility and resilience
```

## Data Flow

```
┌─────────────────────────────────────────────────────┐
│                Content Script                        │
│                                                      │
│  1. Compute host, schemaHash                        │
│  2. loadFormMemory(host, schemaHash)                │
│     └─> Local FormMemoryEntry or null              │
│                                                      │
│  3. fetchLearningProfile(host, schemaHash)          │
│     └─> Server LearningProfile or null             │
│                                                      │
│  4. mergeSelectorMaps(server, local)                │
│     └─> Effective SelectorMap (local wins)         │
│                                                      │
│  5. For each form field:                            │
│     a. Check effectiveSelectorMap[selector]         │
│     b. If found → use that semantic                 │
│     c. If not → run heuristics                      │
│                                                      │
│  6. Apply autofill with learned mappings            │
└─────────────────────────────────────────────────────┘
```

## Example Scenarios

### Scenario 1: Server profile available, local memory empty
- Server returns: `{ "input[name='q1']": "first_name" }`
- Local memory: `{}`
- **Result:** Uses server mapping for q1

### Scenario 2: Local memory overrides server
- Server returns: `{ "input[name='q1']": "first_name" }`
- Local memory: `{ "input[name='q1']": "preferred_name" }`
- **Result:** Uses "preferred_name" (local wins)

### Scenario 3: Server profile unavailable
- Server returns: `null` (404 or network error)
- Local memory: `{ "input[name='q1']": "first_name" }`
- **Result:** Uses local memory, falls back to heuristics

### Scenario 4: Both empty
- Server returns: `null`
- Local memory: `{}`
- **Result:** Pure heuristics (Phase 1.0 behavior)

## Testing

### Unit Tests
```bash
# Run vitest tests
npm test -- mergeMaps.test.ts
npm test -- profileClient.test.ts
```

### E2E Tests
```bash
# Run Playwright tests
npm run test:e2e -- learning-profile.spec.ts
```

### Manual Testing
1. Start API: `cd services/api && python -m uvicorn app.main:app --reload`
2. Start extension dev server: `cd apps/extension-applylens && npm run dev`
3. Load extension in Chrome
4. Navigate to a test form
5. Open DevTools Network tab
6. Trigger autofill
7. Verify:
   - GET request to `/api/extension/learning/profile?host=...&schema_hash=...`
   - POST request to `/api/extension/learning/sync` after autofill

## API Contract

### GET /api/extension/learning/profile

**Query Parameters:**
- `host` - Domain (e.g., "example.com")
- `schema_hash` - Form schema hash

**Response (200):**
```json
{
  "host": "example.com",
  "schema_hash": "abc123",
  "canonical_map": {
    "input[name='q1']": "first_name",
    "input[name='q2']": "last_name"
  },
  "style_hint": {
    "gen_style_id": "concise_bullets_v2",
    "confidence": 0.9
  }
}
```

**Response (404):**
```json
{
  "detail": "No profile found for this form"
}
```

**Client Behavior:**
- 200 → Parse and use canonical_map
- 404 → Return `null`, fall back to FormMemory
- Network error → Return `null`, fall back to FormMemory

## Performance Considerations

1. **Caching:** Profile client fetches on every `scanAndSuggest`. Consider adding client-side cache:
   ```typescript
   const profileCache = new Map<string, LearningProfile>();
   const cacheKey = `${host}:${schemaHash}`;

   if (profileCache.has(cacheKey)) {
     profile = profileCache.get(cacheKey);
   } else {
     profile = await fetchLearningProfile(host, schemaHash);
     if (profile) profileCache.set(cacheKey, profile);
   }
   ```

2. **Parallel Fetching:** FormMemory and profile can be fetched in parallel:
   ```typescript
   const [memory, profile] = await Promise.all([
     loadFormMemory(host, schemaHash),
     fetchLearningProfile(host, schemaHash),
   ]);
   ```

3. **Timeout:** Profile fetch has implicit timeout from browser. Consider explicit timeout:
   ```typescript
   const profile = await Promise.race([
     fetchLearningProfile(host, schemaHash),
     new Promise(resolve => setTimeout(() => resolve(null), 3000)),
   ]);
   ```

## Next Steps

### Phase 2.2: User Authentication
- Replace temp UUID with actual user_id
- Add auth token to profile requests
- Per-user profile isolation

### Phase 3.0: Active Learning
- Track which server suggestions were accepted/rejected
- Send feedback to improve aggregation
- A/B test different gen_styles

### Phase 3.1: Prefetching
- Fetch profiles for common domains on extension load
- Build local profile cache
- Reduce latency on first autofill

## Troubleshooting

### Profile not fetching
- Check Network tab: Is request being made?
- Check response: 200 or 404?
- Check CORS: Should be allowed for `http://localhost:5175`

### Wrong mappings used
- Check merge logic: Local should override server
- Check FormMemory: Is local cache stale?
- Check aggregator: Is server profile up to date?

### Extension not triggering
- Check content script injection
- Check `scanAndSuggest` is being called
- Check browser console for errors

## Related Documentation

- [Phase 1.5 Implementation](../services/api/LEARNING_IMPLEMENTATION.md)
- [Phase 2.0 Database](../services/api/PHASE_2.0_READY.md)
- [Aggregator Logic](../services/api/app/autofill_aggregator.py)
- [Backend Router](../services/api/app/routers/extension_learning.py)
