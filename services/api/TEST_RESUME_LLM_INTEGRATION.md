# Resume LLM Integration - Test Summary

## ✅ Completed Implementation

### 1. LLM Extraction Function
- **File**: `app/services/resume_parser.py`
- **Function**: `extract_profile_from_resume_llm(resume_text: str) -> ExtractedProfile`
- **Model**: OpenAI `gpt-4o-mini` (temperature=0.2, max_tokens=1000)
- **Test**: ✅ Passed `tests/test_resume_llm_extraction.py`
  ```
  INFO:app.services.resume_parser:LLM extracted profile: 15 skills, Leo Klemet
  Extracted: Leo Klemet, 15 skills, 3 roles
  ```

### 2. Resume Upload Endpoint Integration
- **File**: `app/routers/resume.py`
- **Endpoint**: `POST /api/resume/upload`
- **Behavior**:
  1. Extracts raw text from PDF/DOCX/TXT
  2. Calls heuristic parser for baseline data
  3. **Calls LLM extractor** (if `COMPANION_LLM_ENABLED=1`)
  4. **Merges LLM data** into resume profile:
     - Skills: Union of heuristic + LLM (sorted)
     - Headline: Override with LLM if available
     - Summary: Override with LLM if available
     - Years Experience: From LLM estimation
     - **URLs**: GitHub, Portfolio, Website (NEW in v0.8.11)
     - **Target Roles**: Top 3 roles from LLM (NEW in v0.8.11)
  5. Stores in `resume_profiles` table
  6. Returns comprehensive response

### 3. Database Schema Updates
- **Migration**: `990a4d77d1af_add_github_url_portfolio_url_website_.py`
- **New Columns Added to `resume_profiles`**:
  - `github_url` (Text, nullable)
  - `portfolio_url` (Text, nullable)
  - `website_url` (Text, nullable)
  - `target_roles` (JSON, nullable) - Array of role strings
- **Migration Status**: ✅ Applied to production database

### 4. Response Schema Updates
- **Schema**: `ResumeProfileResponse`
- **New Fields**:
  ```python
  github_url: Optional[str]
  portfolio_url: Optional[str]
  website_url: Optional[str]
  target_roles: Optional[list[str]]
  ```
- **Updated Endpoints**:
  - `POST /api/resume/upload` ✅
  - `GET /api/resume/current` ✅
  - `POST /api/resume/activate/{profile_id}` ✅
  - `GET /api/resume/all` ✅

### 5. Deployment
- **Image**: `leoklemet/applylens-api:0.8.11-resume-urls`
- **Status**: ✅ Deployed to production
- **Container**: `applylens-api-prod` running on http://0.0.0.0:8003
- **Environment**: `COMPANION_LLM_ENABLED=1`, `COMPANION_LLM_MODEL=gpt-4o-mini`
- **Dependencies**: openai==2.9.0 installed ✅

## 📊 Extracted Profile Fields

The LLM extracts the following fields from resume text:

| Field | Type | Example | Source |
|-------|------|---------|--------|
| `full_name` | str | "Leo Klemet" | LLM parsed |
| `headline` | str | "AI/ML Engineer & Full-Stack Developer" | LLM parsed |
| `location` | str | "Herndon, VA, US" | LLM parsed |
| `years_experience` | int | 8 | LLM estimated |
| `skills` | list[str] | ["Python", "FastAPI", "React", ...] | LLM extracted (10-30 skills) |
| `top_roles` | list[str] | ["ML Engineer", "Data Scientist", "AI Engineer"] | LLM extracted (top 3) |
| `github_url` | str | "https://github.com/leoklemet" | LLM extracted |
| `portfolio_url` | str | "https://portfolio.example.com" | LLM extracted |
| `website_url` | str | "https://personal-site.com" | LLM extracted |
| `linkedin_url` | str | "https://linkedin.com/in/leoklemet" | LLM extracted |
| `twitter_url` | str | "https://twitter.com/username" | LLM extracted |
| `summary` | str | "Experienced ML engineer with 8+ years..." | LLM generated (2-4 sentences) |

## 🧪 Manual Testing Instructions

### Test 1: Upload Resume via UI
1. Go to ApplyLens Profile page: http://localhost:8003 (or production URL)
2. Upload your resume (PDF/DOCX)
3. Check browser DevTools Network tab for `/api/resume/upload` response
4. **Verify JSON response includes**:
   - `skills`: Array with 10-30+ skills
   - `target_roles`: Array with 3 roles
   - `github_url`, `portfolio_url`, `website_url`: URLs if present in resume
   - `headline`: Professional headline
   - `summary`: 2-4 sentence summary

### Test 2: Check Current Resume
```bash
# Get auth token from browser (Application > Cookies > session_id)
curl -H "Cookie: session_id=YOUR_SESSION_TOKEN" \
  http://localhost:8003/api/resume/current | jq
```

**Expected fields in response**:
```json
{
  "id": 123,
  "name": "Leo Klemet",
  "headline": "AI/ML Engineer & Full-Stack Developer",
  "experience_years": 8,
  "skills": ["Python", "FastAPI", "React", "TypeScript", ...],
  "target_roles": ["ML Engineer", "Data Scientist", "AI Engineer"],
  "github_url": "https://github.com/leoklemet",
  "portfolio_url": "https://portfolio.example.com",
  "website_url": "https://personal-site.com",
  "summary": "Experienced ML engineer with 8+ years in AI/ML...",
  ...
}
```

### Test 3: Verify LLM Extraction Logs
```bash
docker logs applylens-api-prod | grep "LLM extracted"
```

**Expected output**:
```
INFO:app.services.resume_parser:LLM extracted profile: 15 skills, Leo Klemet
INFO:app.routers.resume:LLM extracted: name=Leo Klemet, skills=15, roles=3
INFO:app.routers.resume:Merged LLM data: 20 total skills, years_exp=8, roles=3, urls=[github=True, portfolio=True, website=True]
```

### Test 4: Extension Auto-Fill (Next Step)
1. Install ApplyLens browser extension
2. Navigate to a job application form (Greenhouse/Lever)
3. Click "Scan Form" → "Generate"
4. **Verify extension console logs**:
   ```
   [v0.3] Loaded user profile: yes
   [v0.3] Profile data: Leo Klemet, 8 years, 20 skills, 3 roles
   [v0.3] URLs: github=true, portfolio=true, website=true
   ```
5. **Verify form fields auto-filled with**:
   - Name: "Leo Klemet"
   - GitHub URL: From profile
   - Portfolio URL: From profile
   - Website URL: From profile
   - Years of experience: 8
   - Skills: Long answers should reference your 20+ skills

## 🔄 Integration Flow

```
User uploads resume (PDF/DOCX/TXT)
    ↓
POST /api/resume/upload
    ↓
Extract text (PyPDF2/python-docx)
    ↓
Heuristic parsing (baseline)
    ↓
LLM extraction (OpenAI gpt-4o-mini) ← ENABLED
    ↓
Merge data (skills union, URLs, roles)
    ↓
Store in resume_profiles table
    ↓
Return comprehensive profile
    ↓
Extension fetches via /api/profile/me
    ↓
Auto-fill form fields with profile data
```

## 📝 Sample Resume Created

Location: `C:\Users\pierr\AppData\Local\Temp\tmpxh5ut2.txt`

Contains:
- Leo Klemet's contact info (phone: 2024401027, email: leoklemet.pa@gmail.com)
- Location: Herndon, VA, US
- 8 years of experience
- 20+ skills (Python, FastAPI, React, TypeScript, PostgreSQL, Docker, etc.)
- 3 top roles (ML Engineer, Full-Stack Developer, AI Engineer)
- URLs (GitHub, portfolio, LinkedIn)
- Professional summary

## 🚀 Next Steps

1. **Manual Upload Test**: Upload resume via UI and verify all fields populate
2. **Extension Integration**: Update `/api/profile/me` to pull from active ResumeProfile
3. **Form Auto-Fill**: Test extension auto-fill on Greenhouse/Lever forms
4. **Purple Badges**: Verify "Profile" source badges appear on auto-filled fields
5. **LLM Context**: Confirm AI answers use 20+ skills in context for better responses

## 📚 Related Files

- `app/services/resume_parser.py` - LLM extraction logic
- `app/routers/resume.py` - Upload endpoint with LLM integration
- `app/models.py` - ResumeProfile model (lines 963-1000)
- `tests/test_resume_llm_extraction.py` - LLM extraction tests
- `alembic/versions/990a4d77d1af_*.py` - Database migration
- `test_llm_resume_upload.ps1` - Manual test script

## ✅ Status: DEPLOYED & READY FOR TESTING

All backend changes are complete and deployed. Ready for manual end-to-end testing!
