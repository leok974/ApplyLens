# v0.3 Release Notes: Memory & Cover Letters

## Overview
v0.3 transforms ApplyLens Companion into a personal assistant for job applications by adding:
- **Client-side memory** that remembers your preferences per site
- **AI-powered cover letter generation** with job description extraction
- **UX polish** with field toggles, source indicators, and smart defaults

## New Features

### 1. Memory System (Per-Site Defaults)
- **IndexedDB storage**: Separate database (`applylens-companion-v3`) for field preferences
- **Memory keys**: Normalized per-site patterns (e.g., `jobs.lever.co/jobs/*`)
  - Automatically replaces numeric and UUID segments with `*`
  - Same memory key for all jobs on a given ATS pattern
- **Instant suggestions**: Load saved preferences immediately on scan (no backend call needed)
- **Learning loop**: Apply button saves all applied values to memory for next visit
- **Precedence**: Memory > AI (saved preferences always preferred)

### 2. Cover Letter Generation
- **Job description extraction**: 4-strategy extraction system
  1. `og:description` meta tag
  2. ATS-specific selectors (Lever, Greenhouse, Workday, Ashby)
  3. Largest content block heuristic
  4. Body text fallback
- **API integration**: `POST /api/extension/cover-letter` endpoint
  - Request: `{job_title, company, job_description, job_url}`
  - Response: `{text: "Generated cover letter..."}`
- **Editable modal**: Rich textarea UI for review and editing
- **Apply/Copy actions**: One-click apply to page or copy to clipboard

### 3. UX Improvements
- **Field toggles**: Checkbox per field to control what gets applied
  - Sensitive fields (SSN, DOB) unchecked by default
  - User can selectively apply only desired fields
- **Source indicators**: Visual badges showing data origin
  - 💾 "Saved preference" (green) for memory
  - 🤖 "AI suggestion" (blue) for backend
- **Smart AI requests**: Only request AI for fields without memory
  - Faster UX, reduced API calls
  - Cover letter always regenerated (even if previously saved)
- **Button states**: Disable/enable logic for better feedback
  - Generate button shows "Generating..." state
  - Cover letter button shows "Regenerating..." after first use

## Architecture

### New Files
1. **`memoryV3.js`** (235 lines)
   - IndexedDB wrapper for field preferences
   - `buildMemoryKey()`: Pathname normalization
   - `saveFieldPreference()`: Store user's final choice
   - `loadPreferences()`: Retrieve all preferences for a memory key
   - Separate from v0.1 bandit system (intentionally not modified)

2. **`jobExtractor.js`** (152 lines)
   - Multi-strategy job description extraction
   - ATS-specific selectors for major platforms
   - `extractRequirements()`, `extractBenefits()` helpers
   - 4000 character truncation for API payload

### Modified Files
1. **`contentV2.js`**
   - Memory loading on scan (instant suggestions)
   - Smart AI request filtering (only fields without memory)
   - Memory-AI merge strategy (memory takes precedence)
   - Apply button saves all values to memory
   - Cover letter button handler with modal UI

2. **`panelV2.js`**
   - Checkbox column for field toggles
   - Source indicators (💾/🤖 badges)
   - `showCoverLetterModal()`: Rich textarea UI
   - Apply function respects checkbox state
   - Cover letter button in footer (purple styling)

3. **`manifest.json`**
   - Version bumped to 0.3.0
   - Added memoryV3.js and jobExtractor.js to content_scripts
   - Updated description to mention memory and cover letters

## User Flow

### First Visit to a Job Site
1. User scans form → Extension detects 8 fields
2. No memory exists yet → Show "No saved preferences"
3. User clicks Generate → AI suggests all 8 fields
4. User reviews suggestions, unchecks SSN field
5. User clicks Apply → 7 fields filled (SSN skipped)
6. **Memory saved**: 7 preferences stored with memory key `jobs.lever.co/jobs/*`

### Return Visit (Different Job, Same Site)
1. User scans form → Extension detects 8 fields
2. **Memory loaded**: 7 preferences from previous visit
3. Panel shows instant suggestions (💾 badges) for 7 fields
4. User clicks Generate → AI only requests 1 field (SSN, not in memory)
5. Merge: 7 memory + 1 AI = 8 total suggestions
6. User clicks Apply → All 8 fields filled
7. **Memory updated**: Now includes SSN preference

### Cover Letter Flow
1. User clicks "📝 Cover Letter" button
2. Extension extracts job description from page
3. API generates personalized cover letter
4. Modal shows editable textarea with generated text
5. User reviews and edits as needed
6. User clicks "Apply to Page" → Cover letter fills textarea on form
7. Or user clicks "Copy to Clipboard" → Ready to paste elsewhere

## Technical Details

### Memory Key Examples
```javascript
// Lever job
location.href = "https://jobs.lever.co/company/1234567-software-engineer"
memoryKey = "jobs.lever.co/jobs/*-software-engineer"

// Greenhouse job
location.href = "https://boards.greenhouse.io/company/jobs/9876543"
memoryKey = "boards.greenhouse.io/company/jobs/*"

// Workday job
location.href = "https://company.myworkdayjobs.com/en-US/External/job/Senior-Engineer_R-12345"
memoryKey = "company.myworkdayjobs.com/en-US/External/job/*"
```

### IndexedDB Schema
```javascript
// Database: applylens-companion-v3
// Store: field-preferences
{
  id: "jobs.lever.co/jobs/*::email",
  memoryKey: "jobs.lever.co/jobs/*",
  canonicalField: "email",
  value: "user@example.com",
  pageUrl: "https://jobs.lever.co/company/1234567-software-engineer",
  updatedAt: 1735776000000
}
```

### Memory-AI Merge Strategy
```javascript
// Scan detects 8 fields
const fields = [...];

// Load memory (instant)
const memoryPrefs = await loadPreferences(memoryKey);
// memoryPrefs = { email: "...", phone: "...", linkedin: "..." }

// Show memory suggestions immediately
renderFields(panel, fields, {
  email: { value: "...", source: "memory" },
  phone: { value: "...", source: "memory" },
  linkedin: { value: "...", source: "memory" }
});

// Generate button: Only request AI for fields without memory
const fieldsNeedingAI = fields.filter(f =>
  f.canonical && (!memoryPrefs[f.canonical] || f.canonical === "cover_letter")
);
const aiSuggestions = await generateSuggestions(fieldsNeedingAI, jobContext);

// Merge with precedence (memory > AI)
const merged = { ...memoryPrefs, ...aiSuggestions };
renderFields(panel, fields, merged);
```

## Testing Checklist

### Manual Testing
- [ ] First visit: Scan → Generate → Apply → Verify memory saved
- [ ] Return visit: Scan → Verify memory loaded instantly
- [ ] Memory merge: Generate → Verify only missing fields requested
- [ ] Field toggles: Uncheck field → Apply → Verify field skipped
- [ ] Cover letter: Generate → Edit → Apply to page
- [ ] Cover letter: Copy to clipboard
- [ ] Different job, same site → Verify same memory key
- [ ] IndexedDB inspection: Check stored preferences

### Unit Tests (Pending)
- [ ] `tests/memoryV3.test.ts`: buildMemoryKey normalization
- [ ] `tests/memoryV3.test.ts`: save/load IndexedDB operations
- [ ] `tests/jobExtractor.test.ts`: Multi-strategy extraction
- [ ] `tests/jobExtractor.test.ts`: ATS-specific selectors

### E2E Tests (Pending)
- [ ] `e2e/memory-persistence.spec.ts`: Full memory cycle
- [ ] `e2e/cover-letter-generation.spec.ts`: Modal flow

## Backend Requirements

### New Endpoint Needed
```python
# POST /api/extension/cover-letter
@router.post("/cover-letter")
async def generate_cover_letter(
    request: CoverLetterRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate personalized cover letter using GPT-4

    Request:
        job_title: str
        company: str
        job_description: str
        job_url: str

    Response:
        text: str (generated cover letter)
    """
    # TODO: Implement in services/api
    pass
```

## Next Steps

### v0.4 Roadmap (Pending)
1. **Turbo Apply**: One-click scan → memory+AI → apply
   - Button only shows if memory exists for site
   - Confirmation dialog before auto-fill
   - Summary: "Applied X fields from memory, Y from AI"

2. **Debug Mode**: Toggle to show selectors and sources
   - Checkbox in panel header
   - Shows field selectors in table
   - Shows memory key in console
   - Shows extraction strategy for job description

3. **Unit Tests**: Comprehensive test coverage
   - Memory key normalization edge cases
   - IndexedDB mocking for save/load
   - Job extraction with mocked DOM
   - Merge strategy with various precedence scenarios

4. **E2E Tests**: Real browser testing
   - Playwright tests for memory persistence
   - Cover letter generation flow
   - Multi-visit scenarios

## Known Limitations

1. **Backend dependency**: Cover letter generation requires new API endpoint
2. **Memory privacy**: All preferences stored locally (IndexedDB), no server sync
3. **Memory conflicts**: No conflict resolution if user applies different values for same field
4. **Cover letter length**: Truncated at 4000 chars to fit API payload
5. **ATS coverage**: Memory works on all sites, but cover letter extraction optimized for 5 major platforms

## Migration Notes

### v0.2 → v0.3
- No breaking changes to v0.2 API
- v0.1 learning system (`learning/formMemory.js`) untouched
- New IndexedDB database (`applylens-companion-v3`) is separate from v0.1
- Users can safely upgrade without losing v0.1 learning data

### Backward Compatibility
- v0.2 Scan → Generate → Apply flow unchanged
- v0.2 ATS presets and field detection unchanged
- v0.2 profile snapshot and logging unchanged
- v0.3 features are additive (memory, cover letters, toggles)
