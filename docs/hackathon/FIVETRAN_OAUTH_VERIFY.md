# Fivetran OAuth Verification Guide

**Purpose:** Verify that the Gmail connector uses **Custom OAuth** (user-provided OAuth app) instead of Fivetran's shared OAuth application.

**Why this matters:** Using your own OAuth app ensures:
- ✅ Higher API rate limits (not shared with other Fivetran users)
- ✅ Better security (credentials under your control)
- ✅ Compliance with Google's OAuth policies for production apps
- ✅ Required for hackathon evidence (custom integration, not shared service)

---

## Quick Start

### Prerequisites

1. **Fivetran API Credentials:**
   - Log into Fivetran → Account Settings → API Config
   - Generate API Key and Secret

2. **Connector ID:**
   - Go to Fivetran → Connectors → Your Gmail connector
   - Copy the connector ID from the URL (e.g., `exchanging_mantra`)

### Run Verification

**Option 1: Node.js Script (Recommended)**

```bash
# PowerShell
$env:FIVETRAN_API_KEY="your_api_key"
$env:FIVETRAN_API_SECRET="your_api_secret"
$env:FIVETRAN_CONNECTOR_ID="your_connector_id"
npm run verify:fivetran:oauth

# Bash/Zsh
export FIVETRAN_API_KEY="your_api_key"
export FIVETRAN_API_SECRET="your_api_secret"
export FIVETRAN_CONNECTOR_ID="your_connector_id"
npm run verify:fivetran:oauth
```

**Option 2: curl Fallback (Manual Inspection)**

```bash
# PowerShell
$env:FIVETRAN_API_KEY="your_api_key"
$env:FIVETRAN_API_SECRET="your_api_secret"
$env:FIVETRAN_CONNECTOR_ID="your_connector_id"
bash scripts/fivetran/verify_oauth.curl

# Bash/Zsh
export FIVETRAN_API_KEY="your_api_key"
export FIVETRAN_API_SECRET="your_api_secret"
export FIVETRAN_CONNECTOR_ID="your_connector_id"
./scripts/fivetran/verify_oauth.curl
```

---

## Expected Output

### ✅ PASS - Custom OAuth Detected

```
🔍 Verifying Fivetran Gmail OAuth configuration...

📡 Fetching connector: exchanging_mantra
────────────────────────────────────────────────────────────
Connector: gmail_lite / exchanging_mantra
Auth: custom_oauth
Evidence: config.use_own_oauth = true, Custom OAuth client_id detected
Last Sync: 2025-10-18T19:21:45Z  Status: connected
Sync Freq: 360  History: last_14_days
📊 Fetching schema information...
   Schemas: 1, Tables: 5/8 enabled

────────────────────────────────────────────────────────────
✅ RESULT: PASS (Custom OAuth detected)

📄 Evidence written to: docs/hackathon/EVIDENCE_FIVETRAN_OAUTH.md
📄 Raw API response saved to: docs/hackathon/oauth_check.json
```

### ❌ FAIL - Shared OAuth Detected

```
🔍 Verifying Fivetran Gmail OAuth configuration...

📡 Fetching connector: exchanging_mantra
────────────────────────────────────────────────────────────
Connector: gmail_lite / exchanging_mantra
Auth: shared
Evidence: Shared OAuth detected
Last Sync: 2025-10-18T19:21:45Z  Status: connected
Sync Freq: 360  History: last_14_days
────────────────────────────────────────────────────────────
❌ RESULT: FAIL (Shared OAuth detected)

Action Required:
  1. Go to Fivetran UI → Connector → Setup
  2. Enable "Use your own OAuth app"
  3. Configure Google OAuth client with redirect URI
  4. Re-authorize and re-run this verifier

See: docs/hackathon/FIVETRAN_OAUTH_VERIFY.md
```

### ⚠️ INCONCLUSIVE - Manual Verification Needed

```
🔍 Verifying Fivetran Gmail OAuth configuration...

📡 Fetching connector: exchanging_mantra
────────────────────────────────────────────────────────────
Connector: gmail_lite / exchanging_mantra
Auth: inconclusive
Last Sync: 2025-10-18T19:21:45Z  Status: connected
Sync Freq: 360  History: last_14_days
────────────────────────────────────────────────────────────
⚠️  RESULT: INCONCLUSIVE (Unable to determine OAuth type)

Manual verification required:
  1. Check Fivetran UI → Connector → Setup → OAuth section
  2. Verify "Use your own OAuth app" is enabled
  3. Review oauth_check.json for raw API response

Evidence fields checked:
  - config.auth_type: OAUTH2
  - config.use_own_oauth: not found
  - authentication.method: not found
```

---

## PASS Criteria

The script prints **`RESULT: PASS`** when it detects any of these indicators:

1. ✅ `config.use_own_oauth = true`
2. ✅ `config.custom_oauth = true`
3. ✅ `authentication.method = custom_oauth` or `user_provided`
4. ✅ Custom `client_id` or `oauth_client_id` present in config

If **any** of these are found, custom OAuth is confirmed.

---

## How to Configure Custom OAuth

If the verifier returns **FAIL** or you need to set up custom OAuth:

### Step 1: Get Fivetran Redirect URI

1. Log into Fivetran
2. Go to **Connectors** → Your Gmail connector
3. Click **Setup** tab
4. Scroll to **OAuth** section
5. Enable **"Use your own OAuth app"**
6. Copy the **Redirect URI** (e.g., `https://fivetran.com/auth/gmail`)

### Step 2: Configure Google OAuth Client

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project (e.g., `applylens-gmail-12345`)
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Name: `Fivetran Gmail Connector`
7. **Authorized redirect URIs**: Paste Fivetran's redirect URI
8. Click **Create**
9. Copy **Client ID** and **Client Secret**

### Step 3: Add Credentials to Fivetran

1. Return to Fivetran connector **Setup** page
2. Paste **Client ID** in the OAuth section
3. Paste **Client Secret**
4. Click **Save**

### Step 4: Re-Authorize Connector

1. Click **Re-authorize** button
2. Sign in with your Gmail account
3. Grant permissions
4. Wait for authorization success

### Step 5: Verify Configuration

```bash
# Re-run verifier
npm run verify:fivetran:oauth

# Should now show: RESULT: PASS ✅
```

---

## Troubleshooting

### Issue: "API request failed: 401 Unauthorized"

**Cause:** Invalid API credentials

**Fix:**
1. Verify `FIVETRAN_API_KEY` and `FIVETRAN_API_SECRET` are correct
2. Check Fivetran → Account Settings → API Config
3. Regenerate credentials if needed

### Issue: "API request failed: 404 Not Found"

**Cause:** Invalid connector ID

**Fix:**
1. Go to Fivetran → Connectors
2. Click your Gmail connector
3. Copy connector ID from URL (e.g., `exchanging_mantra`)
4. Update `FIVETRAN_CONNECTOR_ID` environment variable

### Issue: "Rate limiting detected"

**Cause:** Gmail API rate limits exceeded

**Fix:**
1. Reduce history window to 7-14 days:
   - Fivetran → Connector → Setup → History Mode: `last_14_days`
2. Increase sync interval:
   - Set sync frequency to 6 hours instead of hourly
3. Limit labels synced:
   - Exclude promotional, spam, and low-value labels
4. See `RUNBOOK.md` for detailed configuration

### Issue: "INCONCLUSIVE - Unable to determine OAuth type"

**Cause:** Fivetran API schema changed or custom field names

**Fix:**
1. Open `docs/hackathon/oauth_check.json`
2. Manually inspect the JSON for OAuth-related fields
3. Look for fields like:
   - `use_own_oauth`
   - `custom_oauth`
   - `client_id`
   - `oauth_app_type`
4. If found, update `verify_oauth.mjs` detection logic
5. Or verify manually in Fivetran UI:
   - Connector → Setup → OAuth section
   - Check if "Use your own OAuth app" is toggled ON

---

## Evidence File Location

After running the verifier, evidence is saved to:

- **Evidence report:** `docs/hackathon/EVIDENCE_FIVETRAN_OAUTH.md`
- **Raw API response:** `docs/hackathon/oauth_check.json`

### Evidence File Contents

The evidence file includes:

1. ✅ PASS/FAIL result
2. 📋 Connector details (ID, service, status, sync frequency)
3. 🔍 OAuth detection evidence (fields checked, values found)
4. 📊 Schema information (enabled tables count)
5. ⚠️ Rate limiting warnings (if detected)
6. 📄 Redacted API response (sensitive fields removed)
7. 📝 Next steps (action items if FAIL)

### Example Evidence File

````markdown
# Fivetran OAuth Verification Evidence

**Verification Date:** 2025-10-18T20:15:30.123Z  
**Connector ID:** exchanging_mantra  
**Service:** gmail_lite

## Result

**Status:** ✅ PASS  
**Auth Type:** custom_oauth  
**Custom OAuth Detected:** Yes

**Evidence:**
- config.use_own_oauth = true
- Custom OAuth client_id detected

## Connector Details

- **Service:** gmail_lite
- **Connector ID:** exchanging_mantra
- **Status:** connected
- **Last Sync:** 2025-10-18T19:21:45Z
- **Sync Frequency:** 360
- **History Mode:** last_14_days

## Schema Information

- **Schemas:** 1
- **Total Tables:** 8
- **Enabled Tables:** 5
````

---

## For Devpost Submission

### Required Screenshots

1. **Fivetran Connector Setup Page:**
   - Show "Use your own OAuth app" toggle enabled
   - Highlight OAuth section with client ID visible (redact secret)

2. **Evidence File:**
   - Screenshot of `EVIDENCE_FIVETRAN_OAUTH.md` showing PASS result

3. **Google OAuth Configuration:**
   - Google Cloud Console → Credentials
   - Show OAuth 2.0 client with Fivetran redirect URI

4. **Verification Command Output:**
   - Terminal showing successful verification run
   - `RESULT: PASS (Custom OAuth detected)` message visible

### Devpost Description Bullet

Add this to your hackathon submission:

> **Custom OAuth Integration:** Gmail connector uses dedicated OAuth app (not shared) for enhanced security, compliance, and API rate limits. Verified via automated Fivetran API check with evidence documentation.

---

## npm Script

The root `package.json` includes this convenience script:

```json
{
  "scripts": {
    "verify:fivetran:oauth": "node scripts/fivetran/verify_oauth.mjs"
  }
}
```

**Usage:**
```bash
# Set environment variables first
npm run verify:fivetran:oauth
```

---

## API Details

### Endpoint

```
GET https://api.fivetran.com/v1/connectors/{connector_id}
```

### Authentication

HTTP Basic Auth with API key/secret:
```
Authorization: Basic base64(api_key:api_secret)
```

### Response Schema

Key fields examined for OAuth detection:

```json
{
  "data": {
    "id": "connector_id",
    "service": "gmail_lite",
    "config": {
      "auth_type": "OAUTH2",
      "use_own_oauth": true,          // ← Custom OAuth indicator
      "custom_oauth": true,            // ← Custom OAuth indicator
      "client_id": "xxx",              // ← Presence indicates custom OAuth
      "sync_frequency": 360,
      "history_mode": "last_14_days"
    },
    "authentication": {
      "method": "custom_oauth"         // ← Custom OAuth indicator
    },
    "status": {
      "setup_state": "connected",
      "sync_completed_at": "2025-10-18T19:21:45Z"
    }
  }
}
```

### Optional: Schema Endpoint

```
GET https://api.fivetran.com/v1/connectors/{connector_id}/schemas
```

Returns table counts for evidence file.

---

## Files Created

This verification system creates:

1. **`scripts/fivetran/verify_oauth.mjs`** - Automated Node.js verifier (447 lines)
2. **`scripts/fivetran/verify_oauth.curl`** - curl fallback script (40 lines)
3. **`docs/hackathon/FIVETRAN_OAUTH_VERIFY.md`** - This guide (580+ lines)
4. **`docs/hackathon/EVIDENCE_FIVETRAN_OAUTH.md`** - Generated evidence (auto-created on first run)
5. **`docs/hackathon/oauth_check.json`** - Raw API response (auto-created on first run)

---

## Additional Resources

- **Fivetran API Docs:** https://fivetran.com/docs/rest-api/connectors
- **Fivetran OAuth Setup:** https://fivetran.com/docs/connectors/applications/gmail#setup-guide
- **Google OAuth Setup:** https://console.cloud.google.com/apis/credentials
- **ApplyLens Fivetran Guide:** `analytics/fivetran/README.md`

---

## Support

For issues with verification:

1. Check environment variables are set correctly
2. Verify API credentials in Fivetran console
3. Review `oauth_check.json` for raw API response
4. Check Fivetran UI manually (Connector → Setup → OAuth)
5. Update detection logic in `verify_oauth.mjs` if API schema changed

---

**Last Updated:** October 18, 2025  
**Version:** 1.0  
**Status:** Ready for use
