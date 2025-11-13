# Companion E2E Tests

This directory contains E2E tests for the ApplyLens Companion extension's learning loop functionality.

## Test Suites

### `autofill-learning-realworld.spec.ts` - Real World Learning Flow ✅

**Tag**: `@companion @realworld`

**Purpose**: Exercises a realistic Companion flow where the aggregator has already produced canonical mappings.

**Flow**:
1. Mock `/api/extension/learning/profile` as if the aggregator has already produced a canonical map.
2. Load `test/demo-form.html` with the extension content script.
3. Open the Companion panel, run Scan/Suggest.
4. Click **Fill All**:
   - Fields are filled via `generate-form-answers`.
   - `trackAutofillCompletion()` runs.
   - `flushLearningEvents()` calls `/api/extension/learning/sync`.
5. The spec asserts:
   - Profile endpoint was called.
   - Sync endpoint was called with a valid payload.
   - Form fields contain the generated answers.

**What it proves**: The full loop works from the extension's perspective without needing a real DB or aggregator run.

**Run it**:
```bash
npx playwright test -g "@realworld"
```

### `autofill-learning-lowquality.spec.ts` - Low Quality Profile Guardrails ✅

**Tag**: `@companion @lowquality`

**Purpose**: Verifies that the extension gracefully handles low-quality profiles that would be rejected by backend quality guards.

**Flow**:
1. Mock `/api/extension/learning/profile` to return a profile with low quality metrics:
   - `success_rate: 0.2` (< 0.6 threshold)
   - `avg_edit_chars: 900` (> 500 threshold)
   - `confidence: 0.1` (very low)
2. Load demo form and trigger autofill.
3. Click **Fill All**.
4. The spec asserts:
   - Profile endpoint was called (we tried to fetch it).
   - System fell back to heuristics (generated answers work).
   - Learning sync still fires (we learn from this run).
   - Form fields are filled correctly using heuristic answers.

**What it proves**: Quality guards work - extension doesn't break when given bad profile data, falls back gracefully, and continues learning.

**Run it**:
```bash
npx playwright test -g "@lowquality"
```

### `autofill-ux-panel.spec.ts` - Panel UX Controls ⏳

**Tag**: `@companion @ux`

**Status**: ⚠️ **SPECIFICATION TEST** - Describes Phase 3.0 feature to be implemented

**Purpose**: Validates Phase 3.0 per-field accept/edit controls in the Companion panel.

**Flow**:
1. Mock `/api/extension/generate-form-answers` to return deterministic answers.
2. Open demo form and trigger Companion panel.
3. Verify answer rows are rendered with checkboxes and textareas.
4. **Uncheck** first row (should NOT be filled).
5. **Edit** second row textarea to a custom value.
6. Click **Fill All**.
7. Assert:
   - First row's field remains empty (unchecked).
   - Second row's field contains the edited value.

**What it proves**: Per-field UX controls (checkboxes and inline editing) correctly drive Fill All behavior.

**Implementation Requirements**:
- Panel must render `[data-testid="al-answer-row"]` for each answer
- Each row must have `data-selector="<css-selector>"` attribute
- Each row must contain:
  - `[data-testid="al-answer-checkbox"]` - checkbox to enable/disable field
  - `[data-testid="al-answer-textarea"]` - editable text area
- Fill All logic must respect checkbox state and use textarea values

**Run it**:
```bash
npx playwright test -g "@ux"
```

### `autofill-generation-guardrails.spec.ts` - Generation Guardrails ⏳

**Tag**: `@companion @generation`

**Status**: ⚠️ **SPECIFICATION TEST** - Describes Phase 3.1 feature to be implemented

**Purpose**: Validates Phase 3.1 backend guardrails that sanitize generated content.

**Flow**:
1. Mock `/api/extension/generate-form-answers` to return sanitized content (simulating backend guardrails).
2. Open demo form and trigger Companion panel.
3. Click **Fill All**.
4. Assert form fields contain sanitized content:
   - No "I worked at" phrases.
   - No `http://` or `https://` URLs.
   - Safe content like company names remain.

**What it proves**: Backend guardrails successfully strip forbidden phrases and URLs before content reaches the form.

**Implementation Requirements**:
- Backend `/api/extension/generate-form-answers` must apply guardrails module
- Guardrails must strip:
  - URLs matching `http://` or `https://` patterns
  - Forbidden phrases like "I worked at"
- Sanitization must preserve safe content

**Run it**:
```bash
npx playwright test -g "@generation"
```

**Tests included**:
- Basic guardrails validation (single violation)
- Multiple violations handling (URLs + forbidden phrases)

## Running Tests

### All Companion Tests
```bash
npm run e2e:companion
```

### Specific Test Tags
```bash
# Real world flow only
npx playwright test -g "@realworld"

# Low quality profile tests
npx playwright test -g "@lowquality"

# UX panel controls
npx playwright test -g "@ux"

# Generation guardrails
npx playwright test -g "@generation"

# Run UX and generation tests together
npx playwright test -g "@ux|@generation"
```

### With UI (headed mode)
```bash
npx playwright test e2e/autofill-learning-realworld.spec.ts --headed
```

## Test Architecture

### Content Script Loading
Tests use a patched version of `content.js` that replaces ES module imports with inline stubs:
- `APPLYLENS_API_BASE` → hardcoded test URL
- Learning modules → stubbed implementations that make actual HTTP requests
- Profile client → inline fetch implementation

### Chrome API Stubbing
The chrome extension APIs are mocked via `page.evaluate()`:
- `chrome.storage.sync.get()` → returns `{ learningEnabled: true }`
- `chrome.runtime.sendMessage()` → returns success
- Injected after page load to ensure availability

### Key Insights
- **Timing matters**: Chrome API must be injected via `page.evaluate()` AFTER page load, not `addInitScript()`
- **Console logs**: Use `page.on('console')` to capture browser logs for debugging
- **Fill All required**: Learning sync only triggers when Fill All button is clicked, not on scan

## Adding New Tests

When creating new Companion tests:

1. **Tag appropriately**: Add `@companion` tag to the test suite description
2. **Reuse helpers**: Copy the content script patching and Chrome API stubbing patterns
3. **Capture console**: Enable console forwarding for debugging
4. **Test the full flow**: Don't just test API calls - verify DOM changes too

Example:
```typescript
test.describe("@companion @myfeature", () => {
  test("my new companion test", async ({ page }) => {
    // Enable console log capture
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('[CONTENT]') || text.includes('[Learning]')) {
        console.log(text);
      }
    });

    // ... rest of test
  });
});
```

## Related Files

- `../content.js` - Main extension content script
- `../learning/` - Learning module implementations
- `../test/demo-form.html` - Test fixture form
- `../playwright.config.ts` - Playwright configuration
