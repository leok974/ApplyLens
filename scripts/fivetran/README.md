# Fivetran OAuth Verification - Quick Reference

## Quick Commands

### PowerShell (Windows)

```powershell
# Option 1: Using parameters
.\scripts\fivetran\verify_oauth.ps1 `
  -ApiKey "your_api_key" `
  -ApiSecret "your_api_secret" `
  -ConnectorId "your_connector_id"

# Option 2: Using environment variables
$env:FIVETRAN_API_KEY = "your_api_key"
$env:FIVETRAN_API_SECRET = "your_api_secret"
$env:FIVETRAN_CONNECTOR_ID = "your_connector_id"
.\scripts\fivetran\verify_oauth.ps1

# Option 3: Using npm script (after setting env vars)
npm run verify:fivetran:oauth
```

### Bash/Zsh (Linux/Mac)

```bash
# Option 1: One-liner with inline vars
FIVETRAN_API_KEY="xxx" FIVETRAN_API_SECRET="yyy" FIVETRAN_CONNECTOR_ID="zzz" \
  node scripts/fivetran/verify_oauth.mjs

# Option 2: Export environment variables
export FIVETRAN_API_KEY="your_api_key"
export FIVETRAN_API_SECRET="your_api_secret"
export FIVETRAN_CONNECTOR_ID="your_connector_id"
npm run verify:fivetran:oauth

# Option 3: Using curl fallback
./scripts/fivetran/verify_oauth.curl
```

---

## Getting Credentials

### Fivetran API Key/Secret

1. Log into Fivetran: https://fivetran.com
2. Click profile icon → **Account Settings**
3. Navigate to **API Config** tab
4. Click **Generate API Key**
5. Copy **API Key** and **API Secret** (shown only once!)

### Connector ID

1. Go to Fivetran → **Connectors**
2. Click your **Gmail** connector
3. Copy connector ID from URL:
   - Example URL: `https://fivetran.com/dashboard/connectors/exchanging_mantra`
   - Connector ID: `exchanging_mantra`

---

## Expected Results

### ✅ PASS - Custom OAuth Configured

```
Connector: gmail_lite / exchanging_mantra
Auth: custom_oauth
Evidence: config.use_own_oauth = true
RESULT: PASS (Custom OAuth detected)
```

**Action:** Take screenshot for Devpost submission ✅

---

### ❌ FAIL - Using Shared OAuth

```
Connector: gmail_lite / exchanging_mantra
Auth: shared
RESULT: FAIL (Shared OAuth detected)
```

**Action Required:**

1. **Enable Custom OAuth:**
   - Fivetran → Connector → Setup → Toggle "Use your own OAuth app"
   
2. **Get Redirect URI from Fivetran**
   
3. **Configure Google OAuth Client:**
   - Google Cloud Console → APIs & Services → Credentials
   - Create OAuth 2.0 Client ID
   - Add Fivetran redirect URI
   
4. **Add Client ID/Secret to Fivetran**
   
5. **Re-authorize connector**
   
6. **Re-run verification** ✅

---

### ⚠️ INCONCLUSIVE - Manual Check Needed

```
Connector: gmail_lite / exchanging_mantra
Auth: inconclusive
RESULT: INCONCLUSIVE (Unable to determine OAuth type)
```

**Action:** Check Fivetran UI manually:
- Connector → Setup → OAuth section
- Verify "Use your own OAuth app" is enabled

---

## Troubleshooting

### "Missing required environment variables"

**Fix:** Set all three variables:
```powershell
$env:FIVETRAN_API_KEY = "your_key"
$env:FIVETRAN_API_SECRET = "your_secret"
$env:FIVETRAN_CONNECTOR_ID = "your_connector_id"
```

### "API request failed: 401 Unauthorized"

**Fix:** Regenerate API credentials in Fivetran

### "API request failed: 404 Not Found"

**Fix:** Verify connector ID from Fivetran URL

### "Rate limiting detected"

**Fix:**
- Reduce history window to 7-14 days
- Increase sync interval to 6 hours
- Limit synced labels

---

## Output Files

After running verification:

1. **Evidence Report:**
   - `docs/hackathon/EVIDENCE_FIVETRAN_OAUTH.md`
   - Contains PASS/FAIL result, connector details, next steps

2. **Raw API Response:**
   - `docs/hackathon/oauth_check.json`
   - Full JSON for manual inspection

---

## For Devpost Submission

### Required Screenshots

1. ✅ Fivetran connector setup showing "Use your own OAuth app" enabled
2. ✅ Evidence file with PASS result
3. ✅ Google OAuth client with Fivetran redirect URI
4. ✅ Terminal output showing verification success

### Description Bullet

> **Custom OAuth Integration:** Gmail connector verified to use dedicated OAuth app (not Fivetran's shared app) via automated API check. Enhanced security, compliance, and API rate limits. Evidence: `docs/hackathon/EVIDENCE_FIVETRAN_OAUTH.md`

---

## Files Created

- `scripts/fivetran/verify_oauth.mjs` - Node.js verifier (447 lines)
- `scripts/fivetran/verify_oauth.ps1` - PowerShell wrapper
- `scripts/fivetran/verify_oauth.curl` - curl fallback
- `docs/hackathon/FIVETRAN_OAUTH_VERIFY.md` - Full documentation
- `docs/hackathon/EVIDENCE_FIVETRAN_OAUTH.md` - Generated evidence

---

## Documentation

- **Full Guide:** `docs/hackathon/FIVETRAN_OAUTH_VERIFY.md`
- **Fivetran Setup:** `analytics/fivetran/README.md`
- **Evidence Pack:** `docs/hackathon/EVIDENCE.md`

---

**Quick Start:**
```powershell
# 1. Get credentials (see above)
# 2. Set environment variables
# 3. Run verification
npm run verify:fivetran:oauth
```
