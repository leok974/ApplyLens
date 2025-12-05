# Resume Contact → Profile → Extension Integration

## Status: ✅ Extension Ready

The extension is already configured to consume contact fields from the profile API.

## How It Works

### 1. Backend Flow (API v0.8.5-resume-contact)
```
Resume Upload → Parse Contact Info → Merge into ResumeProfile → Expose via /api/profile/me
```

New fields in ResumeProfile:
- `name` (String) - Full name from resume
- `email` (String) - Email address
- `phone` (String) - Phone number
- `linkedin` (Text) - LinkedIn URL

### 2. Extension Consumption

**Profile Fetch** (`contentV2.js:120-144`):
```js
const userProfile = await fetchProfile(); // GET /api/profile/me
```

**Field Mapping** (`contentV2.js:385-421`):
```js
const getProfileValue = (canonical, profile) => {
  // Name splitting
  if (canonical === 'first_name') return profile.name.split(' ')[0];
  if (canonical === 'last_name') return profile.name.split(' ').slice(1).join(' ');

  // Direct mappings
  if (canonical === 'email') return profile.email;
  if (canonical === 'phone') return profile.phone;
  if (canonical === 'linkedin') return profile.linkedin;
  // ... etc
};
```

**Auto-Fill** (`contentV2.js:432-447`):
- Profile fields get `source: "profile"`
- Auto-selected in panel (green "Profile" chip)
- Applied to form with one click

## Testing Checklist

### After API Deployment

1. **Upload Resume**
   - Go to ApplyLens web app
   - Upload resume with contact info
   - Verify `/api/resume/current` returns `name`, `email`, `phone`, `linkedin`

2. **Check Profile API**
   ```bash
   curl -H "Authorization: Bearer $TOKEN" https://api.applylens.app/api/profile/me
   ```
   Should include contact fields from active resume profile

3. **Test Extension**
   - Open a job application form (Greenhouse, Lever, etc.)
   - Click extension icon → Scan form
   - Verify:
     - First Name shows "Profile" chip (indigo) with your first name
     - Last Name shows "Profile" chip with your last name
     - Email shows "Profile" chip with your email
     - Phone shows "Profile" chip with your phone
     - LinkedIn shows "Profile" chip with your LinkedIn URL
   - All profile fields should be auto-checked
   - Click "Apply to Page" → fields should fill correctly

## Current Profile Structure

The extension expects this from `/api/profile/me`:

```json
{
  "name": "Leo Klemet",           // NEW - from resume
  "email": "leo@example.com",     // NEW - from resume
  "phone": "+33 6 12 34 56 78",   // NEW - from resume
  "linkedin": "https://linkedin.com/in/leoklemet", // NEW - from resume
  "headline": "AI/ML Engineer · Agentic systems · Full-stack",
  "locations": ["Paris, France", "Remote EU"],
  "target_roles": ["AI Engineer", "ML Engineer"],
  "tech_stack": ["Python", "TypeScript", ...],
  "projects": [...],
  "preferences": {
    "domains": [...],
    "work_setup": [...]
  }
}
```

## Fallback Behavior

If backend hasn't deployed yet:
- Extension gracefully handles missing fields (returns `null`)
- No errors, just fewer auto-filled fields
- Users can still use memory/AI suggestions

## Next Steps

1. ✅ Backend: Deploy API v0.8.5-resume-contact
2. ✅ Extension: Already supports new fields (no changes needed)
3. ⏳ Testing: Verify end-to-end flow
4. 🎯 Enhancement: Add GitHub/portfolio extraction to backend parser
