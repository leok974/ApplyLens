## ApplyLens Companion v0.2 – Job Form Mode

**Goal**: Make the extension truly usable on real job application sites (Lever, Greenhouse, Workday, Ashby, generic forms) with a clean **Scan → Generate → Apply** workflow.

---

### What's New in v0.2

✅ **Smart Field Detection**
- Canonical field types (email, phone, linkedin, cover_letter, etc.)
- ATS-specific presets for Lever, Greenhouse, Workday, Ashby, SmartRecruiters
- Robust label detection using multiple strategies
- Automatic company and job title extraction

✅ **3-Step Workflow**
1. **Scan** - Detect all form fields and map to canonical types
2. **Generate** - Get AI suggestions from your ApplyLens profile
3. **Apply** - Review, edit, and apply suggestions to the page

✅ **Log Applications**
- One-click logging to ApplyLens Tracker
- Automatic job title and company extraction

✅ **Better UX**
- Visual ATS badge (shows Lever/Greenhouse/etc.)
- Editable suggestions before applying
- Profile/sensitive field indicators
- Graceful error handling

---

### How to Try It

#### 1. Build the Extension

```bash
cd apps/extension-applylens
pnpm install
pnpm build  # or pnpm test to run unit tests first
```

#### 2. Load Unpacked in Chrome

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Select the `apps/extension-applylens` directory
5. Extension should appear with ApplyLens icon

#### 3. Test on a Real Job Site

**Recommended test sites:**
- Lever: https://jobs.lever.co/anthropic (or any Lever job)
- Greenhouse: https://boards.greenhouse.io/openai (or any Greenhouse job)
- Workday: Search "myworkdayjobs.com" on Google
- Ashby: https://jobs.ashbyhq.com/lattice (or any Ashby job)

**Steps:**
1. Navigate to any job application page on a supported ATS
2. Click the ApplyLens extension icon in your toolbar
3. Verify:
   - 🟢 "Connected to ApplyLens" status (green)
   - Profile shows your name/email
4. Click **"🚀 Scan Form (v0.2)"** button
5. Panel appears on the right side of the page showing:
   - Detected ATS badge (Lever/Greenhouse/etc.)
   - Table of all form fields with:
     - Field labels
     - Canonical types (email, phone, linkedin, etc.)
     - Current values
     - Empty suggestion column

#### 4. Generate Suggestions

1. Click **"Generate Suggestions"** button
2. Wait a few seconds (button shows "Generating...")
3. Suggestions appear in the right column
4. Green success message: "Suggestions generated! Review and edit before applying."
5. **Edit any suggestions directly in the table** (click into text inputs/textareas)

#### 5. Apply to Page

1. Review all suggestions (edit as needed)
2. Click **"Apply to Page"** button
3. Green success message shows count: "Applied 8 fields to the page! ✓"
4. Form fields on the page are now filled with your data
5. Verify the values look correct

#### 6. Log Application

1. Click **"Log Application"** button
2. Green success: "Application logged to ApplyLens Tracker ✓"
3. Open https://applylens.app/tracker to see the logged application

---

### Field Detection Details

**Canonical Field Types:**
- **Profile fields** (auto-filled from your profile):
  - `full_name`, `first_name`, `last_name`
  - `email`, `phone`, `location`
  - `linkedin`, `github`, `portfolio`, `website`
  - `headline`, `summary`

- **Generated fields** (AI-generated per job):
  - `cover_letter`
  - `years_experience`, `notice_period`
  - `visa_status`, `work_authorization`
  - `remote_preference`, `relocation`

- **Sensitive fields** (marked, not auto-filled):
  - `salary_expectation`
  - `pronouns`
  - `diversity_gender`, `diversity_race`, `diversity_veteran`, `diversity_disability`

**ATS-Specific Handling:**

- **Lever**:
  - "Additional Information" → `cover_letter`
  - `cards[...][field0]` with "Name" label → `full_name`

- **Greenhouse**:
  - Clean IDs like `#first_name`, `#email` work perfectly
  - `#cover_letter` → `cover_letter`
  - File inputs (resume) are skipped

- **Workday**:
  - Cryptic IDs (`#input-1`, `#input-2`) rely on label text
  - "Email Address" → `email`
  - "Phone Number" → `phone`
  - Complex address fields are skipped

- **Ashby**:
  - "Why do you want to...?" questions → `cover_letter`

---

### Testing Checklist

- [ ] Extension loads without errors
- [ ] Popup shows health status (green = connected)
- [ ] Profile loads (shows your name/email)
- [ ] Open a Lever job → Click "Scan Form (v0.2)"
  - [ ] Panel appears with "Lever" badge
  - [ ] Fields table shows detected fields
  - [ ] Canonical types are correct (email, phone, etc.)
- [ ] Click "Generate Suggestions"
  - [ ] Button shows "Generating..."
  - [ ] Suggestions appear in table
  - [ ] Can edit suggestions inline
- [ ] Click "Apply to Page"
  - [ ] Form fields on page are filled
  - [ ] Success message appears
- [ ] Click "Log Application"
  - [ ] Success message appears
  - [ ] Check Tracker at applylens.app - application is logged
- [ ] Repeat for Greenhouse, Workday, Ashby
- [ ] Test error handling:
  - [ ] Disconnect network → "Generate" shows error
  - [ ] Log out of applylens.app → "Generate" shows "Not logged in"

---

### Known Limitations (v0.2)

**Backend Endpoints:**
- ❌ `/api/extension/form/suggestions` - **Does not exist yet**
  - Extension will show error: "Server error (404)"
  - Needs backend implementation (see below)
- ❌ `/api/extension/log-application` - **Does not exist yet**
  - Same error, needs implementation

**Workarounds for Testing:**
1. Test field detection without "Generate" button (just scan and review canonical mappings)
2. Manually fill suggestions in the table to test "Apply to Page" flow
3. Backend team needs to implement these endpoints ASAP

**Other Limitations:**
- No cover letter generation yet (will use generic template from profile)
- No "save my edits" persistence (coming in v0.3)
- No bandit/learning integration (intentionally deferred)
- File upload fields are detected but not filled (by design)
- Checkbox/radio fields not supported yet (coming soon)

---

### Backend Requirements

The v0.2 extension expects these endpoints:

#### 1. `POST /api/extension/form/suggestions`

**Purpose**: Generate autofill suggestions for form fields

**Request:**
```json
{
  "url": "https://jobs.lever.co/company/job-id",
  "title": "Senior Software Engineer",
  "company": "Acme Corp",
  "fields": [
    {
      "canonical": "email",
      "label": "Email Address",
      "type": "email",
      "current_value": ""
    },
    {
      "canonical": "cover_letter",
      "label": "Cover Letter",
      "type": "textarea",
      "current_value": ""
    }
  ]
}
```

**Response:**
```json
{
  "suggestions": {
    "email": "user@example.com",
    "phone": "+1234567890",
    "full_name": "John Doe",
    "linkedin": "https://linkedin.com/in/johndoe",
    "cover_letter": "Dear Hiring Manager,\n\nI am excited to apply for the Senior Software Engineer position at Acme Corp...",
    "years_experience": "5",
    "visa_status": "Authorized to work in the US"
  }
}
```

**Implementation Notes:**
- Use `/api/profile/me` to get user's profile data
- For profile fields (email, phone, etc.): return from profile directly
- For generated fields (cover_letter): use GPT-4 with job context + user profile
- For unknown/missing fields: omit from response
- Sensitive fields: don't include unless explicitly requested

#### 2. `POST /api/extension/log-application`

**Purpose**: Log an application to the tracker

**Request:**
```json
{
  "url": "https://jobs.lever.co/company/job-id",
  "title": "Senior Software Engineer",
  "company": "Acme Corp",
  "source": "extension",
  "notes": "Logged from Companion v0.2"
}
```

**Response:**
```json
{
  "id": "app_123abc",
  "created_at": "2025-12-03T10:30:00Z"
}
```

**Implementation Notes:**
- Create or update Application record
- Link to user's profile
- Set `source = "extension"`
- Store URL for deduplication
- Return the application ID for confirmation

---

### Next Steps (Post-v0.2)

**v0.3 - Cover Letter Generation**
- Dedicated cover letter generation endpoint with context
- "Regenerate cover letter" button in panel
- Save preferred tone/style per user

**v0.4 - Learning Integration**
- "Save my edits as defaults" button
- Per-site field mapping persistence
- Integrate with existing learning loop

**v0.5 - Advanced Fields**
- Checkbox/radio field support
- Select dropdown handling
- Multi-page form detection

**Production Release**
- CI/CD for extension builds
- Automated testing with Playwright
- Chrome Web Store submission
- Usage analytics (privacy-friendly)

---

### Troubleshooting

**Panel doesn't appear:**
- Check console for errors (F12 → Console tab)
- Verify you're on a supported ATS site (Lever, Greenhouse, etc.)
- Try refreshing the page and clicking "Scan Form" again

**Fields not detected:**
- Check if fields are visible (not in collapsed sections)
- Try scrolling to make fields visible before scanning
- Check console for `[Scanner]` logs showing detected fields

**"Generate Suggestions" fails with 404:**
- Backend endpoint not implemented yet (expected)
- Test field detection and "Apply to Page" flow manually for now

**Applied values don't stick:**
- Some ATS platforms use React/Vue - try clicking into the field after apply
- Check if field is readonly or disabled
- Verify the field selector is still valid (page didn't re-render)

**"Log Application" fails:**
- Backend endpoint not implemented yet (expected)
- Or: not logged in to applylens.app (sign in first)

---

### Code Structure (v0.2)

```
apps/extension-applylens/
├── schema.js              # Canonical field types & inference
├── atsPresets.js          # ATS-specific field detection tweaks
├── fieldScanner.js        # Main field scanning logic
├── panelV2.js             # Panel UI & API calls
├── contentV2.js           # Orchestration (Scan → Generate → Apply)
├── popup.js               # Extension popup (v0.2 button added)
├── manifest.json          # Extension manifest (v0.2 scripts added)
└── tests/
    ├── schema.test.ts     # Unit tests for field inference
    └── atsPresets.test.ts # Unit tests for ATS presets
```

**Backward Compatibility:**
- Old "Scan form & suggest answers (legacy)" button still works
- v0.1 learning/bandit code is untouched
- Can run both v0.1 and v0.2 side-by-side for testing

---

### Success Criteria

✅ Extension can scan fields on Lever, Greenhouse, Workday, Ashby
✅ Field inference correctly maps email, phone, linkedin, cover_letter
✅ Panel shows fields table with canonical types
✅ "Apply to Page" successfully fills form fields
✅ Job context (title, company) extracted correctly
✅ Unit tests pass for schema inference and ATS presets
✅ No console errors during normal operation
✅ Graceful error handling for network/auth failures

---

**Ready to dogfood!** 🚀

Once backend endpoints are implemented, this becomes a real productivity tool for applying to jobs.
