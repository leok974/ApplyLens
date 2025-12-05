# ApplyLens Future Enhancements

This document outlines planned enhancements for ApplyLens, with detailed implementation guidance.

## Status Overview

### ✅ Completed
- [x] Profile-aware LLM integration
- [x] Source attribution (Profile/Learned/AI chips)
- [x] Source summary bar with counts
- [x] Years of experience extraction from resume
- [x] Contact fields (name, email, phone, LinkedIn) from resume

### 📋 Planned

#### 1. Education & Certifications
**Status**: Not started
**Priority**: Medium
**Effort**: 3-4 hours

**Backend Changes** (services/api/):
- Add `education` (JSONB) column to `user_profiles` table
- Add `certifications` (JSONB) column to `user_profiles` table
- Create migration: `add_education_certifications_to_profiles.py`
- Update Pydantic schemas:
  ```python
  class EducationEntry(BaseModel):
      school: str
      degree: Optional[str] = None
      field: Optional[str] = None
      start_year: Optional[int] = None
      end_year: Optional[int] = None

  class CertificationEntry(BaseModel):
      name: str
      issuer: Optional[str] = None
      year: Optional[int] = None
  ```
- Update `FormProfileContext` to include education/certifications
- Update LLM prompt builder to include education/certifications

**Web UI Changes** (apps/web/):
- Add education section to profile form (textarea or structured editor)
- Add certifications section to profile form
- Save as JSON arrays to API

**Extension Changes** (apps/extension-applylens/):
- Update `buildLLMProfileContext()` to include:
  ```js
  education: profile.education || [],
  certifications: profile.certifications || [],
  ```
- These will automatically flow to LLM via existing profile context pipeline

**Testing**:
1. Add education in web UI → Save → Check `/api/profile/me` response
2. Generate suggestions on form with education question
3. Verify LLM uses education context in answer

---

#### 2. Skills Extraction from Resume
**Status**: Not started
**Priority**: High
**Effort**: 2-3 hours

**Backend Changes** (services/api/):
- Create `app/services/skills_extractor.py`:
  ```python
  SKILL_LEXICON = {
      "python", "javascript", "typescript", "react", "vue",
      "node.js", "fastapi", "django", "flask", "sql",
      "postgres", "docker", "kubernetes", "aws", "gcp",
      "pytorch", "tensorflow", "langchain", "openai",
      # ... add more
  }

  def extract_skills_from_text(text: str) -> List[str]:
      lower = text.lower()
      found = set()
      for skill in SKILL_LEXICON:
          if skill in lower:
              found.add(skill)
      return sorted(found)
  ```

- Update `app/routers/resume.py` upload handler:
  ```python
  from app.services.skills_extractor import extract_skills_from_text

  # After extracting resume text:
  skills = extract_skills_from_text(resume_text)
  if skills:
      existing = set(profile.tech_stack or [])
      merged = sorted(existing.union(skills))
      profile.tech_stack = merged
      db.commit()
  ```

**No Extension Changes Needed**:
- Extension already sends `tech_stack` in profile context
- Skills will automatically appear in LLM prompts

**Testing**:
1. Upload resume mentioning "Python, FastAPI, React, Docker"
2. Check profile → `tech_stack` should include those skills
3. Generate suggestions → LLM should mention those skills in answers

**Future Enhancement**:
- Use LLM to extract skills instead of lexicon matching
- Extract skill proficiency levels (beginner/intermediate/expert)
- Extract years of experience per skill

---

#### 3. Job-Specific Customization (Tone & Length)
**Status**: Not started
**Priority**: Medium
**Effort**: 4-5 hours

**Popup UI** (apps/extension-applylens/popup.html):
```html
<section class="space-y-2">
  <h3 class="text-xs font-semibold">Answer Style</h3>

  <div class="flex flex-col gap-1">
    <label class="text-[11px] text-slate-400">Tone</label>
    <select id="companion-tone" class="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs">
      <option value="concise">Concise & direct</option>
      <option value="confident">Confident & assertive</option>
      <option value="friendly">Friendly & warm</option>
      <option value="detailed">Detailed & explanatory</option>
    </select>
  </div>

  <div class="flex flex-col gap-1">
    <label class="text-[11px] text-slate-400">Length</label>
    <select id="companion-length" class="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs">
      <option value="short">Short (1-3 sentences)</option>
      <option value="medium">Medium (1-2 paragraphs)</option>
      <option value="long">Long (2-4 paragraphs)</option>
    </select>
  </div>
</section>
```

**Popup JS** (apps/extension-applylens/popup.js):
```js
const TONE_KEY = "companion_tone";
const LENGTH_KEY = "companion_length";

// Load settings
chrome.storage.sync.get([TONE_KEY, LENGTH_KEY], (data) => {
  const toneSelect = document.getElementById("companion-tone");
  const lengthSelect = document.getElementById("companion-length");

  if (data[TONE_KEY]) toneSelect.value = data[TONE_KEY];
  if (data[LENGTH_KEY]) lengthSelect.value = data[LENGTH_KEY];
});

// Save on change
document.getElementById("companion-tone").addEventListener("change", (e) => {
  chrome.storage.sync.set({ [TONE_KEY]: e.target.value });
});

document.getElementById("companion-length").addEventListener("change", (e) => {
  chrome.storage.sync.set({ [LENGTH_KEY]: e.target.value });
});
```

**Content Script** (apps/extension-applylens/contentV2.js):
```js
// Add helper to fetch style prefs
function getStylePrefs() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(
      ["companion_tone", "companion_length"],
      (data) => {
        resolve({
          tone: data["companion_tone"] || "concise",
          length: data["companion_length"] || "medium",
        });
      }
    );
  });
}

// Update generateSuggestions() to include style prefs
async function generateSuggestions(fields, jobContext, userProfile = null) {
  const profileContext = buildLLMProfileContext(userProfile);
  const stylePrefs = await getStylePrefs(); // NEW

  const response = await sendExtensionMessage({
    type: "API_PROXY",
    payload: {
      url: "/api/extension/generate-form-answers",
      method: "POST",
      body: {
        job: { ... },
        fields: [ ... ],
        profile_context: profileContext,
        style_prefs: stylePrefs,  // NEW
      },
    }
  });

  // ... rest unchanged
}
```

**Backend API** (services/api/):
```python
# app/schemas/extension.py
class StylePrefs(BaseModel):
    tone: str = "concise"  # concise | confident | friendly | detailed
    length: str = "medium"  # short | medium | long

class FormAnswersRequest(BaseModel):
    job: JobContext
    fields: List[FormFieldSpec]
    profile_context: Optional[FormProfileContext] = None
    style_prefs: Optional[StylePrefs] = None  # NEW

# app/services/form_llm.py
def build_style_instructions(sp: Optional[StylePrefs]) -> str:
    if not sp:
        return "Tone: concise and clear.\nLength: short (1-3 sentences)."

    tone_map = {
        "concise": "Concise and direct.",
        "confident": "Confident and assertive, but not arrogant.",
        "friendly": "Friendly, warm, and approachable (still professional).",
        "detailed": "Detailed and explanatory, with enough context.",
    }
    length_map = {
        "short": "Short: 1-3 sentences.",
        "medium": "Medium: 1-2 paragraphs.",
        "long": "Long: 2-4 paragraphs, with clear structure.",
    }

    tone = tone_map.get(sp.tone, tone_map["concise"])
    length = length_map.get(sp.length, length_map["medium"])

    return f"Tone: {tone}\nLength: {length}"

def build_form_answers_prompt(req: FormAnswersRequest) -> List[dict]:
    style_text = build_style_instructions(req.style_prefs)

    system_text = (
        "You are ApplyLens Companion. You help fill job application forms.\n"
        f"{style_text}\n"
        # ... rest of system prompt
    )

    # ... rest unchanged
```

**Visual Indicator** (apps/extension-applylens/panelV2.js):
Add style badge to panel header:
```js
// After source summary bar
const stylePrefs = await getStylePrefs();
const styleBadge = `
  <span class="text-[10px] text-slate-400">
    Tone: <span class="text-slate-200">${stylePrefs.tone}</span> ·
    Length: <span class="text-slate-200">${stylePrefs.length}</span>
  </span>
`;
```

**Testing**:
1. Change tone to "Friendly" in popup
2. Change length to "Long"
3. Generate suggestions on form with "Why do you want to work here?"
4. Verify answer is friendly in tone and 2-4 paragraphs long
5. Change to "Concise" + "Short"
6. Regenerate → should be 1-3 sentences

---

## Implementation Priority

**Phase 1** (Immediate - High ROI):
1. Skills extraction from resume (2-3 hours)
   - Direct value: Better LLM context
   - No UI changes needed
   - Low risk

**Phase 2** (Near-term - User-facing value):
2. Job-specific customization (4-5 hours)
   - High user value: Control over answer style
   - Visible differentiation from competitors
   - Requires full-stack changes

**Phase 3** (Medium-term - Nice to have):
3. Education & certifications (3-4 hours)
   - Valuable for academic/research roles
   - Less critical for most SWE positions
   - Can defer until user requests

---

## Notes

- All enhancements build on existing profile context pipeline
- No breaking changes to current functionality
- Each feature is independently deployable
- Extension changes are minimal (mostly just passing data through)
- Heavy lifting is in backend (parsing, prompt engineering)

---

## Future Ideas (Not Prioritized)

- **Cover letter generation**: Full-page cover letter from profile + job
- **Multi-resume support**: Different resumes for different role types
- **A/B testing**: Try different tones/lengths, track success rates
- **Learning from rejections**: Track which answers correlate with interviews
- **Industry-specific templates**: Startup vs enterprise answer styles
- **Resume optimization**: Suggest resume improvements based on target jobs
