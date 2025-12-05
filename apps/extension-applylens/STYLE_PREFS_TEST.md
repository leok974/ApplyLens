# Style Preferences Testing Guide

## Feature: Job-Specific Answer Customization

Users can customize how AI generates answers with tone and length preferences.

## Testing Steps

### 1. Load Extension
1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select `D:\ApplyLens\apps\extension-applylens`
4. Verify extension loads without errors

### 2. Set Style Preferences
1. Click the ApplyLens extension icon in toolbar
2. Navigate to "Settings" tab
3. Locate "Answer Style" section
4. Select **Tone**: Confident & assertive (default)
5. Select **Length**: Medium (default)
6. Verify selections are saved (check console: "Saved tone: confident")

### 3. Test Different Combinations
Try these combinations and verify they're saved:

**Professional & Brief**
- Tone: Confident & assertive
- Length: Short (1-3 sentences)

**Friendly & Detailed**
- Tone: Friendly & warm
- Length: Long (2-4 paragraphs)

**Technical & Concise**
- Tone: Detailed & explanatory
- Length: Short (1-3 sentences)

**Approachable & Moderate**
- Tone: Concise & direct
- Length: Medium (1-2 paragraphs)

### 4. Verify API Integration
1. Open a job application form (e.g., Greenhouse, Lever)
2. Click "Scan Form" in extension popup
3. Open browser DevTools Console
4. Look for log: `[v0.3] Using style: confident tone, medium length`
5. Check Network tab for `/api/extension/generate-form-answers` request
6. Verify request body includes:
   ```json
   {
     "job": {...},
     "fields": [...],
     "profile_context": {...},
     "style_prefs": {
       "tone": "confident",
       "length": "medium"
     }
   }
   ```

### 5. Verify Answer Quality
Compare answers with different settings:

**Short + Concise**
- Answers should be 1-3 sentences
- Direct, no fluff
- Example: "I have 5 years of experience building scalable web applications with React and Node.js."

**Long + Friendly**
- Answers should be 2-4 paragraphs
- Warm, conversational tone
- Example: "I'm excited to share that I've spent the past 5 years deeply immersed in web development... [continues with detailed narrative]"

**Medium + Detailed**
- Answers should be 1-2 paragraphs
- Thorough explanations
- Example: "My professional background includes 5 years of experience in full-stack development. I've worked extensively with modern JavaScript frameworks including React, Vue, and Angular on the frontend..."

## Expected Behavior

### Storage
- Preferences saved to `chrome.storage.sync`
- Persists across browser sessions
- Syncs across Chrome instances (if user is signed in)

### API Request
```json
{
  "job": {
    "url": "https://boards.greenhouse.io/company/jobs/12345",
    "title": "Senior Software Engineer",
    "company": "Acme Corp"
  },
  "fields": [
    {"field_id": "resume_text", "label": "Resume", "type": "textarea"},
    {"field_id": "cover_letter", "label": "Cover Letter", "type": "textarea"}
  ],
  "profile_context": {
    "name": "John Doe",
    "headline": "Senior Software Engineer",
    "experience_years": 5,
    "tech_stack": ["React", "Node.js", "TypeScript"],
    "target_roles": ["Software Engineer", "Full Stack Developer"]
  },
  "style_prefs": {
    "tone": "confident",
    "length": "medium"
  }
}
```

### Console Logs
```
[v0.3] Sending profile context to LLM: John Doe, 5 years, 8 skills, 2 roles
[v0.3] Using style: confident tone, medium length
[v0.3] Generated 6 suggestions from backend
```

## Troubleshooting

### Preferences not saving
- Check DevTools Console for errors
- Verify `chrome.storage.sync` permissions in manifest.json
- Try `chrome.storage.local` if sync is disabled

### API not receiving style_prefs
- Check Network tab for request body
- Verify `getStylePrefs()` is being called before `generateSuggestions()`
- Check for `await` on async function calls

### Answers not matching expected style
- Backend may not yet implement style_prefs logic
- Verify API version supports style customization
- Check backend logs for processing of style_prefs

## Next Steps

After verifying extension sends style_prefs correctly:

1. **Backend Implementation**: Update `/api/extension/generate-form-answers` to use style_prefs in LLM prompt
2. **Prompt Engineering**: Build system prompts for each tone/length combination
3. **Quality Testing**: Compare answer quality across different settings
4. **User Feedback**: Collect feedback on tone/length options, adjust as needed
