# Chrome Web Store Submission Checklist

## Pre-Submission

### 1. Privacy Policy Hosting
- [ ] Upload `public/privacy.html` to `https://applylens.app/extension/privacy`
- [ ] Test URL is publicly accessible
- [ ] Update `manifest.json` if privacy policy URL changes

### 2. Screenshots & Assets
Create and upload to `https://applylens.app/extension/assets/`:
- [ ] `screen1.png` (1280x800) - Scan forms & suggest answers
- [ ] `screen2.png` (1280x800) - Draft recruiter DMs
- [ ] `screen3.png` (1280x800) - Browser Companion settings & activity
- [ ] `promo-1280x800.png` - Promotional tile for store listing

Screenshot tips:
- Show the extension in action with realistic data
- Highlight key features (autofill, DM generation, activity tracking)
- Use clean, professional mockups
- Add captions/annotations if helpful

### 3. Build Production Package
```powershell
cd D:\ApplyLens\apps\extension-applylens
.\pack.ps1
```

Output: `dist/applylens-companion-YYYYMMDD-HHmmss.zip`

### 4. Test Production Build
1. Go to `chrome://extensions`
2. Remove dev version
3. Load unpacked from `dist/` (extract ZIP first)
4. Test all features:
   - [ ] Profile loads in popup
   - [ ] Form scanning works on Greenhouse/Lever
   - [ ] DM generation works on LinkedIn
   - [ ] Applications/outreach log correctly
   - [ ] Settings page shows activity

## Chrome Developer Dashboard

### Account Setup
1. Go to [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole/)
2. Sign in with Google account: **leoklemet.pa@gmail.com**
3. Pay one-time $5 developer registration fee (if not already paid)

### New Item Submission

#### Store Listing Tab
Copy from `store-listing.json`:

**Extension name:**
```
ApplyLens Companion – Autofill job applications & recruiter DMs
```

**Summary:** (132 char max)
```
Smart autofill for Greenhouse/Lever/Workday and tailored recruiter DMs using your ApplyLens profile.
```

**Description:**
```
ApplyLens Companion helps you move faster:

• Scan job application forms (Greenhouse, Lever, Workday, and more) and suggest concise, relevant answers using your ApplyLens profile
• Draft tailored recruiter DMs for LinkedIn
• (Optional) Log applications and outreach to your ApplyLens tracker

Privacy-first:
• Only captures metadata you choose to log (company, role, job URL, recruiter name/profile, short DM preview)
• No selling of data; no background browsing history; no sensitive info collection
• All communication is HTTPS; you can delete logs anytime from ApplyLens

Get started:
1) Install the extension
2) Open a job application page → click the extension → "Scan form & suggest"
3) On LinkedIn profile pages → "Draft recruiter DM" → copy/paste

Support: leoklemet.pa@gmail.com
```

**Category:** Productivity

**Language:** English

#### Privacy Practices Tab

**Privacy policy URL:**
```
https://applylens.app/extension/privacy
```

**Single purpose description:**
```
ApplyLens Companion autofills job application forms and drafts personalized recruiter messages using your ApplyLens profile data.
```

**Permissions justification:**

**`activeTab`**
```
Only when you click the extension, reads visible fields to generate answers.
```

**`scripting`**
```
Injects the content script on the current tab to scan fields and fill suggestions.
```

**`host_permissions` for https://*.greenhouse.io/***
```
Greenhouse is a common ATS platform. Extension scans job forms to autofill with personalized answers.
```

**`host_permissions` for https://jobs.lever.co/***
```
Lever is a common ATS platform. Extension scans job forms to autofill with personalized answers.
```

**`host_permissions` for https://*.myworkdayjobs.com/***
```
Workday is a common ATS platform. Extension scans job forms to autofill with personalized answers.
```

**`host_permissions` for https://www.linkedin.com/***
```
Used to draft personalized recruiter DMs based on profile information.
```

**`host_permissions` for https://applylens.app/* and https://api.applylens.app/***
```
Connects to ApplyLens API to fetch user profile and log application/outreach activity.
```

#### Data Use

**Does this extension collect or transmit user data?** YES

**Data types collected:**
- [ ] User activity (Company name, Role title, Job URL, Timestamps)
- [ ] Personal info (Recruiter name, LinkedIn profile URL, Short DM preview)

**Data sharing:** NO - "This extension does not share user data with third parties"

**Data selling:** NO - "This extension does not sell user data"

**Data usage:** "This extension uses data to provide and improve its core functionality"

**Prominent disclosure:** YES - Privacy policy clearly states what data is collected

**Secure transmission:** YES - All data transmitted via HTTPS

**Approved use cases:**
- [ ] Provide or improve your service or extension
- [ ] Personalization (e.g., recommendations, tailored content or ads)

**Data deletion:**
```
You can delete logged application/outreach entries from ApplyLens at any time; this removes them from our systems.
```

#### Package Tab
1. Click "Upload new package"
2. Select `dist/applylens-companion-YYYYMMDD-HHmmss.zip`
3. Wait for automated checks to complete

Common issues:
- Manifest errors → check `manifest.json` syntax
- Icon missing → ensure `icons/` folder included
- Service worker errors → test in dev mode first

#### Distribution Tab
**Visibility:** Public (or Unlisted for testing)

**Regions:** All regions (or select specific countries)

**Pricing:** Free

## Post-Submission

### Review Process
- Typically takes 1-3 business days
- Check email for update notifications
- Respond promptly to any reviewer questions

### Common Rejection Reasons
1. **Insufficient privacy disclosure** → Ensure privacy.html is complete
2. **Overly broad permissions** → Justify each host permission
3. **Missing single purpose description** → Be specific about core functionality
4. **Unclear data use** → Explain exactly what data is collected and why

### After Approval
1. Extension appears in Chrome Web Store
2. Users can install via store link
3. Updates require re-submission (same process)

## Testing URLs

Before submission, verify these work:
- [ ] https://applylens.app/extension (homepage)
- [ ] https://applylens.app/extension/privacy (privacy policy)
- [ ] https://applylens.app/extension/support (support page - create if needed)
- [ ] https://applylens.app/extension/assets/screen1.png (screenshot 1)
- [ ] https://applylens.app/extension/assets/screen2.png (screenshot 2)
- [ ] https://applylens.app/extension/assets/screen3.png (screenshot 3)
- [ ] https://applylens.app/extension/assets/promo-1280x800.png (promo tile)

## Resources

- [Chrome Web Store Developer Documentation](https://developer.chrome.com/docs/webstore/)
- [Extension Quality Guidelines](https://developer.chrome.com/docs/webstore/program-policies/)
- [Privacy Policy Requirements](https://developer.chrome.com/docs/webstore/program-policies/privacy/)
- [Troubleshooting Submission Issues](https://developer.chrome.com/docs/webstore/troubleshooting/)
