# ApplyLens Companion — Privacy Policy
**Effective date:** 2025-11-12

ApplyLens Companion ("the extension") helps you speed up job applications by:
- reading visible fields on job application pages,
- drafting short answers based on your profile stored in ApplyLens,
- helping you draft outreach messages on LinkedIn.

We take privacy seriously. This policy explains what the extension collects, how it's used, and your choices.

## What the extension collects

### 1) Application metadata (optional, only when you click "Scan form & suggest" or "Log application")
- Company name, Role title, Job URL (page URL)
- Timestamps (when you clicked)
- **No** passwords, SSNs, or private file uploads are collected.

### 2) Outreach metadata (optional, only when you click "Draft recruiter DM" and choose to log it)
- Recruiter name (you provide), LinkedIn profile URL, a short preview of the drafted message, timestamp

### 3) Profile fetch
- The extension requests your ApplyLens profile from your own ApplyLens API (`/api/profile/me`) to tailor answers.
- This is your data, returned from your server; it's not shared with third parties by the extension.

### 4) Diagnostics (optional)
- Basic error messages (non-PII) may be shown in the UI to help you debug connectivity.

## What we **do not** collect
- Email contents, Gmail credentials, OAuth tokens (the extension doesn't connect to Gmail).
- Sensitive personal info (government IDs, bank details).
- Keystrokes or clipboard contents (other than copying the drafted message when you click "Copy").
- Background browsing history.

## How we use the data
- To generate suggested answers for form fields you opt into scanning.
- To let you log applications/outreach to your ApplyLens account for tracking.
- To improve reliability and show you your recent activity.

We **do not** sell your data. We **do not** share your data with advertisers.

## Data retention & deletion
- Logged application/outreach events are stored in your ApplyLens backend and follow your account's retention rules.
- You can delete logged entries in ApplyLens at any time; deletion removes them from our systems.
- The extension itself stores only minimal transient state in memory while a page is open.

## Security
- HTTPS is required for all communication to your ApplyLens API.
- CSRF protection is enforced on browser flows; machine-to-machine calls use API keys.
- Access control for your ApplyLens data is handled by your ApplyLens backend.

## Your choices
- You can use the extension without logging anything; autofill works without saving events.
- You can disable host permissions or remove the extension at any time in your browser's settings.

## Contact
Questions or requests? Email **leoklemet.pa@gmail.com**.

## Changes to this policy
We may update this policy; we will revise the "Effective date" above and publish updated terms with each extension release.
