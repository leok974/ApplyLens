# Multi-User Gmail Integration & Enhanced Extraction - Complete Guide

**Status**: ✅ Production Ready  
**Date**: October 9, 2025  
**Version**: 2.0

## Table of Contents

1. [Overview](#overview)
2. [What's New](#whats-new)
3. [Quick Start](#quick-start)
4. [Database Migrations](#database-migrations)
5. [Configuration](#configuration)
6. [Multi-User OAuth Setup](#multi-user-oauth-setup)
7. [Single-User Mode (Legacy)](#single-user-mode-legacy)
8. [Mock Mode (Testing)](#mock-mode-testing)
9. [PDF Text Extraction](#pdf-text-extraction)
10. [API Endpoints](#api-endpoints)
11. [Confidence Scoring](#confidence-scoring)
12. [Testing](#testing)
13. [Troubleshooting](#troubleshooting)
14. [Production Recommendations](#production-recommendations)

---

## Overview

ApplyLens now supports **multi-user Gmail integration** with enhanced email extraction capabilities:

- **Multi-user OAuth**: Each user can connect their own Gmail account
- **Enhanced extraction**: Improved heuristics with confidence scoring
- **PDF parsing**: Optional text extraction from PDF attachments
- **Attachment metadata**: Track interview invites and documents
- **Mock provider**: Test without Google API for CI/CD
- **Backward compatible**: Existing single-user setup still works

---

## What's New

### Multi-User OAuth

- Per-user Gmail tokens stored in database
- OAuth flow: `/oauth/google/init` → `/oauth/google/callback`
- Support for `X-User-Email` header or `user_email` in request body
- Graceful fallback to single-user env vars if no user token found

### Enhanced Extraction

- **Subject line hints**: Detects "Greenhouse", "Lever", "Workday" in subject
- **Authentication headers**: Analyzes `Return-Path`, `DKIM-Signature`, `Authentication-Results`
- **PDF attachment hints**: Detects interview invites by filename patterns
- **Improved confidence scoring**: 0.4 (weak) to 0.95 (strong signals)

### PDF Text Extraction

- Optional feature enabled via `GMAIL_PDF_PARSE=True`
- Size guard: `GMAIL_PDF_MAX_BYTES` (default 2MB)
- Uses `pdfminer.six` to extract text from PDFs
- Prepends PDF text to email body for extraction

### Provider Pattern

- **Single-user provider**: Uses env vars (quick start)
- **DB-backed provider**: Per-user tokens from `gmail_tokens` table
- **Mock provider**: For testing without Google API

---

## Quick Start

### 1. Run Migrations

```bash
cd services/api

# Run migrations
python -m alembic upgrade head

# This creates:
# - source_confidence column in applications table
# - gmail_tokens table for multi-user OAuth
```

### 2. Install Dependencies

```bash
pip install pdfminer.six  # Already in pyproject.toml
```

### 3. Configure Environment

Choose one of three modes:

**Option A: Multi-User (Recommended)**

```bash
# In services/api/.env
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
OAUTH_REDIRECT_URI=http://localhost:8003/oauth/google/callback

# Optional: PDF parsing
GMAIL_PDF_PARSE=True
GMAIL_PDF_MAX_BYTES=2097152  # 2MB
```

**Option B: Single-User (Legacy)**

```bash
# In services/api/.env
GMAIL_CLIENT_ID=your-client-id
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REFRESH_TOKEN=your-refresh-token
GMAIL_USER=you@example.com
```

**Option C: Mock (Testing)**

```bash
USE_MOCK_GMAIL=True
```

### 4. Start API

```bash
uvicorn app.main:app --reload --port 8003
```

### 5. Test

```bash
# Extract from email
curl -X POST http://localhost:8003/applications/extract \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Interview for Senior Engineer",
    "from": "recruiting@acme.ai",
    "text": "Thanks for applying to Acme!"
  }'

# Response:
{
  "company": "acme",
  "role": "Senior Engineer",
  "source": null,
  "source_confidence": 0.55,
  "debug": {
    "company_from_header": "acme",
    "matched_role": true,
    "used_gmail": false
  }
}
```

---

## Database Migrations

### Migration 0004: Add source_confidence

```sql
-- Adds confidence score to applications
ALTER TABLE applications
  ADD COLUMN source_confidence REAL NOT NULL DEFAULT 0.5;
```

**File**: `alembic/versions/0004_add_source_confidence.py`

### Migration 0005: Add gmail_tokens Table

```sql
-- Per-user Gmail OAuth tokens
CREATE TABLE gmail_tokens (
  user_email VARCHAR(255) PRIMARY KEY,
  access_token TEXT,
  refresh_token TEXT NOT NULL,
  expiry_date BIGINT,  -- milliseconds since epoch
  scope TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Auto-update updated_at trigger
CREATE TRIGGER gmail_tokens_updated_at_trigger
BEFORE UPDATE ON gmail_tokens
FOR EACH ROW
EXECUTE FUNCTION update_gmail_tokens_updated_at();
```

**File**: `alembic/versions/0005_add_gmail_tokens.py`

**Run migrations**:

```bash
cd services/api
python -m alembic upgrade head
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GMAIL_CLIENT_ID` | ✅ Multi-user | None | Google OAuth client ID |
| `GMAIL_CLIENT_SECRET` | ✅ Multi-user | None | Google OAuth client secret |
| `OAUTH_REDIRECT_URI` | ✅ Multi-user | None | OAuth callback URL |
| `GMAIL_REFRESH_TOKEN` | ⚠️ Single-user | None | Single-user refresh token |
| `GMAIL_USER` | ⚠️ Single-user | None | Single-user email address |
| `GMAIL_PDF_PARSE` | ❌ | `False` | Enable PDF text extraction |
| `GMAIL_PDF_MAX_BYTES` | ❌ | `2097152` | Max PDF size (2MB) |
| `USE_MOCK_GMAIL` | ❌ | `False` | Use mock provider for testing |

### Provider Selection Logic

```
if USE_MOCK_GMAIL:
    → Mock Provider (empty seed)
elif GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET:
    → DB-Backed Provider (multi-user)
    ├─ Has user token? Use user token
    └─ No user token? Fallback to single-user env vars
elif GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET and GMAIL_REFRESH_TOKEN and GMAIL_USER:
    → Single-User Provider (legacy)
else:
    → No Gmail support (use request body only)
```

---

## Multi-User OAuth Setup

### Step 1: Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project or select existing
3. Enable **Gmail API**
4. Go to **APIs & Services** → **Credentials**
5. Click **Create Credentials** → **OAuth client ID**
6. Choose **Web application**
7. Add authorized redirect URI:

   ```
   http://localhost:8003/oauth/google/callback
   ```

   (Or your production callback URL)
8. Save and copy **Client ID** and **Client Secret**

### Step 2: Configure Environment

```bash
# In services/api/.env
GMAIL_CLIENT_ID=123456789-abc123.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-your-secret
OAUTH_REDIRECT_URI=http://localhost:8003/oauth/google/callback
```

### Step 3: User OAuth Flow

**Frontend Implementation**:

```typescript
// In your React app
async function connectGmail(userEmail: string) {
  // 1. Get auth URL
  const res = await fetch(
    `/api/oauth/google/init?user_email=${encodeURIComponent(userEmail)}`
  );
  const { authUrl } = await res.json();
  
  // 2. Open popup or redirect
  window.open(authUrl, 'gmail-oauth', 'width=600,height=700');
  // Or: window.location.href = authUrl;
}
```

**Flow**:

1. User clicks "Connect Gmail"
2. App calls `/oauth/google/init?user_email=user@example.com`
3. App redirects user to Google consent screen
4. User grants permissions
5. Google redirects to `/oauth/google/callback?code=...&state=...`
6. Backend exchanges code for tokens
7. Backend stores tokens in `gmail_tokens` table
8. User sees success page

### Step 4: Using Connected Account

```bash
# Extract with Gmail thread ID
curl -X POST http://localhost:8003/applications/extract \
  -H "Content-Type: application/json" \
  -H "X-User-Email: user@example.com" \
  -d '{"gmail_thread_id": "18f2a3b4c5d6e7f8"}'

# Or pass user_email in body
curl -X POST http://localhost:8003/applications/extract \
  -H "Content-Type: application/json" \
  -d '{
    "gmail_thread_id": "18f2a3b4c5d6e7f8",
    "user_email": "user@example.com"
  }'
```

### Step 5: Check Connection Status

```bash
GET /oauth/google/status?user_email=user@example.com

Response:
{
  "connected": true,
  "user_email": "user@example.com",
  "expires_at": 1730412345000,
  "has_refresh_token": true
}
```

### Step 6: Disconnect

```bash
DELETE /oauth/google/disconnect?user_email=user@example.com

Response:
{
  "success": true,
  "message": "Disconnected Gmail for user@example.com"
}
```

---

## Single-User Mode (Legacy)

For quick setup or single-user deployments, use environment variables.

### Generate Refresh Token

```bash
cd services/api

# Install dependencies
pip install google-auth-oauthlib

# Download credentials.json from Google Cloud Console
# (OAuth client → Download JSON)

# Run this script
python3 -c "
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json',
    scopes=['https://www.googleapis.com/auth/gmail.readonly']
)
creds = flow.run_local_server(port=0)
print('Add these to .env:')
print(f'GMAIL_REFRESH_TOKEN={creds.refresh_token}')
print(f'GMAIL_USER=your-email@gmail.com')
"
```

### Configure

```bash
# In services/api/.env
GMAIL_CLIENT_ID=your-client-id
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REFRESH_TOKEN=1//your-refresh-token
GMAIL_USER=you@gmail.com
```

### Usage

```bash
# No need for X-User-Email header
curl -X POST http://localhost:8003/applications/extract \
  -d '{"gmail_thread_id": "18f2a3b4c5d6e7f8"}'
```

---

## Mock Mode (Testing)

For CI/CD or local development without Google API.

### Enable

```bash
# In services/api/.env
USE_MOCK_GMAIL=True
```

### Seed Mock Data (Optional)

```python
# In tests or startup script
from app.gmail_providers import mock_provider

# Seed threads
mock_threads = {
    "thread123": [{
        "subject": "Interview for Senior Engineer",
        "from": "Acme Recruiting <recruiting@acme.ai>",
        "headers": {"Return-Path": "<mailer@greenhouse.io>"},
        "text": "Thanks for applying!",
        "attachments": [
            {"filename": "Interview_Invite.pdf", "mimeType": "application/pdf", "size": 45213}
        ]
    }]
}

provider = mock_provider(mock_threads)

# Now API calls will return mocked data
```

### Benefits

- ✅ No Google API quota usage
- ✅ Fast tests (no network calls)
- ✅ Deterministic results
- ✅ Works offline

---

## PDF Text Extraction

Optional feature to extract text from PDF attachments.

### Enable

```bash
# In services/api/.env
GMAIL_PDF_PARSE=True
GMAIL_PDF_MAX_BYTES=2097152  # 2MB max
```

### How It Works

1. Gmail provider fetches email with attachments
2. For each PDF attachment under size threshold:
   - Fetch attachment data via Gmail API
   - Decode base64url-encoded bytes
   - Extract text using `pdfminer.six`
   - Prepend to email body text
3. Extractor processes combined text

### Use Cases

- Interview schedules in PDF
- Job descriptions attached
- Offer letters
- Company information packets

### Performance

- **Latency**: +100-300ms per PDF (small files)
- **Quota**: 5 units per attachment fetch
- **Memory**: ~2-5MB per PDF during processing

### Safety

- Size guard prevents memory exhaustion
- Only processes `application/pdf` MIME type
- Graceful error handling (logs but doesn't crash)
- Optional feature (off by default)

---

## API Endpoints

### POST /applications/extract

Extract company, role, source from email (no DB changes).

**Request**:

```json
{
  "gmail_thread_id": "18f2a3b4c5d6e7f8",  // Optional
  "user_email": "user@example.com",       // Optional (or X-User-Email header)
  "subject": "Interview for Engineer",    // Fallback
  "from": "recruiting@acme.ai",           // Fallback
  "text": "Thanks for applying!",         // Fallback
  "headers": {},                           // Fallback
  "attachments": []                        // Fallback
}
```

**Response**:

```json
{
  "company": "acme",
  "role": "Engineer",
  "source": "Greenhouse",
  "source_confidence": 0.95,
  "debug": {
    "company_from_header": "acme",
    "company_from_signature": null,
    "matched_role": true,
    "has_pdf_text": false,
    "used_gmail": true,
    "user_email": "user@example.com"
  }
}
```

### POST /applications/backfill-from-email

Extract and create/update application.

**Request**:

```json
{
  "gmail_thread_id": "18f2a3b4c5d6e7f8",
  "user_email": "user@example.com",
  "company": "Acme",  // Optional override
  "role": "Engineer", // Optional override
  "defaults": {
    "source": "Manual"  // Optional default source
  }
}
```

**Response**:

```json
{
  "saved": {
    "id": 42,
    "company": "Acme",
    "role": "Engineer",
    "source": "Greenhouse",
    "source_confidence": 0.95,
    "status": "applied",
    "thread_id": "18f2a3b4c5d6e7f8",
    "created_at": "2025-10-09T12:00:00Z"
  },
  "extracted": {
    "company": "Acme",
    "role": "Engineer",
    "source": "Greenhouse",
    "source_confidence": 0.95
  },
  "updated": false
}
```

### GET /oauth/google/init

Start OAuth flow for user.

**Request**:

```
GET /oauth/google/init?user_email=user@example.com
```

**Response**:

```json
{
  "authUrl": "https://accounts.google.com/o/oauth2/auth?..."
}
```

### GET /oauth/google/callback

Handle OAuth callback (user lands here after Google consent).

**Request**:

```
GET /oauth/google/callback?code=xxx&state={"user_email":"..."}
```

**Response**:

```html
<html>
  <body>
    <h1>Gmail Connected ✅</h1>
    <p>You can close this window.</p>
  </body>
</html>
```

### GET /oauth/google/status

Check connection status for user.

**Request**:

```
GET /oauth/google/status?user_email=user@example.com
```

**Response**:

```json
{
  "connected": true,
  "user_email": "user@example.com",
  "expires_at": 1730412345000,
  "has_refresh_token": true
}
```

### DELETE /oauth/google/disconnect

Disconnect user's Gmail (delete tokens).

**Request**:

```
DELETE /oauth/google/disconnect?user_email=user@example.com
```

**Response**:

```json
{
  "success": true,
  "message": "Disconnected Gmail for user@example.com"
}
```

---

## Confidence Scoring

Confidence scores range from 0.4 (weak) to 0.95 (strong).

### Scoring Rules

| Signal | Confidence | Notes |
|--------|------------|-------|
| No clear source | 0.4 | Baseline |
| Job keywords in body | 0.55 | "apply", "requisition", "job" |
| ESP detected (SendGrid, SES) | 0.5 | Generic email service |
| Mailing list | 0.6 | Has List-Unsubscribe header |
| PDF interview invite | 0.6 | Filename contains "interview", "invite" |
| DKIM/Auth headers match ATS | 0.85 | Strong authentication signal |
| Known ATS in headers | 0.9 | Greenhouse, Lever, Workday |
| Known ATS in subject | 0.9 | Subject mentions ATS name |
| Known ATS + strong signals | 0.95 | Maximum confidence |

### Examples

**Weak Signal** (0.4):

```
From: unknown@example.com
Subject: Hello
Text: General message
→ source=null, confidence=0.4
```

**Medium Signal** (0.55):

```
From: hr@company.com
Subject: Application update
Text: Thanks for applying to the position
→ source=null, confidence=0.55 (job keywords)
```

**Strong Signal** (0.95):

```
From: notifications@greenhouse.io
Subject: Interview for Senior Engineer
Headers: {
  "Return-Path": "<mailer@greenhouse.io>",
  "DKIM-Signature": "...greenhouse.io..."
}
→ source="Greenhouse", confidence=0.95
```

---

## Testing

### Unit Tests

```python
# tests/test_email_extractor.py
import pytest
from app.email_extractor import extract_from_email, ExtractInput

def test_greenhouse_detection():
    result = extract_from_email(ExtractInput(
        subject="Interview for Engineer",
        from_="Greenhouse <notifications@greenhouse.io>",
        headers={"Return-Path": "<mailer@greenhouse.io>"},
        text="Thanks for applying!"
    ))
    
    assert result.source == "Greenhouse"
    assert result.source_confidence >= 0.9

def test_pdf_attachment_hint():
    result = extract_from_email(ExtractInput(
        subject="Onsite Interview",
        from_="hr@acme.com",
        attachments=[
            {"filename": "Interview_Schedule.pdf", "mimeType": "application/pdf", "size": 50000}
        ]
    ))
    
    assert result.source_confidence >= 0.6
```

### Integration Tests

```python
# tests/test_api_extract.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_extract_endpoint():
    response = client.post("/applications/extract", json={
        "subject": "Interview for Senior Engineer",
        "from": "recruiting@acme.ai",
        "text": "Thanks for applying to Acme!"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["company"] == "acme"
    assert data["role"] == "Senior Engineer"
    assert 0.4 <= data["source_confidence"] <= 1.0
```

### Mock Provider Tests

```python
# tests/test_mock_provider.py
import os
os.environ["USE_MOCK_GMAIL"] = "1"

from app.gmail_providers import mock_provider

def test_mock_provider():
    provider = mock_provider({
        "thread123": [{
            "subject": "Test",
            "from": "test@test.com",
            "text": "Body"
        }]
    })
    
    result = await provider.fetch_thread_latest("thread123")
    assert result["subject"] == "Test"
```

---

## Troubleshooting

### "oauth_not_configured"

**Problem**: Missing OAuth credentials.

**Solution**:

```bash
# Check env vars
env | grep GMAIL

# Ensure these are set:
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
OAUTH_REDIRECT_URI=...
```

### "Invalid state parameter"

**Problem**: State parameter corrupted in OAuth callback.

**Solution**:

- Check redirect URI matches exactly
- Ensure state JSON is valid
- Check for URL encoding issues

### "Token refresh failed"

**Problem**: User's refresh token expired or revoked.

**Solution**:

- User needs to reconnect Gmail (re-consent)
- Delete old token: `DELETE /oauth/google/disconnect`
- Restart OAuth flow: `GET /oauth/google/init`

### "Gmail API error"

**Problem**: Thread not found or permission denied.

**Solution**:

- Verify thread ID is correct
- Check user has access to email
- Ensure Gmail API is enabled in Google Cloud Console
- Check API quota limits

### "pdfminer.six not installed"

**Problem**: PDF parsing enabled but library missing.

**Solution**:

```bash
pip install pdfminer.six
```

### Low Confidence Scores

**Problem**: Extractions have low confidence (<0.6).

**Solution**:

- Check email headers for ATS signals
- Verify subject line has clear patterns
- Look for job-related keywords
- Consider manual source override

---

## Production Recommendations

### Security

1. **Rotate tokens periodically**: Delete and reconnect every 90 days
2. **Encrypt tokens at rest**: Use database encryption for `gmail_tokens`
3. **Rate limit OAuth endpoints**: Prevent abuse
4. **Monitor token usage**: Alert on unusual activity
5. **Use HTTPS**: Always use HTTPS for OAuth callbacks

### Performance

1. **Cache Gmail responses**: Use Redis with 1-hour TTL
2. **Batch token refreshes**: Refresh multiple tokens in background
3. **Database indexes**: Ensure `user_email` indexed in `gmail_tokens`
4. **Connection pooling**: Use SQLAlchemy connection pool
5. **PDF size limits**: Keep `GMAIL_PDF_MAX_BYTES` under 5MB

### Monitoring

```python
# Add to metrics
from prometheus_client import Counter, Histogram

gmail_fetch_duration = Histogram(
    "gmail_fetch_duration_seconds",
    "Time to fetch Gmail thread"
)

gmail_fetch_errors = Counter(
    "gmail_fetch_errors_total",
    "Gmail fetch errors by type",
    ["error_type"]
)

extraction_confidence = Histogram(
    "extraction_confidence",
    "Distribution of confidence scores"
)
```

### Scaling

1. **Service account**: For >1000 users, use Google Workspace service account
2. **Queue processing**: Use Celery for background Gmail fetches
3. **Read replicas**: Use DB read replicas for token lookups
4. **CDN**: Serve OAuth callback page from CDN
5. **Horizontal scaling**: API is stateless, scale horizontally

---

## Summary

✅ **Multi-user OAuth** - Each user connects their own Gmail  
✅ **Enhanced extraction** - Better confidence scoring with multiple signals  
✅ **PDF parsing** - Optional text extraction from attachments  
✅ **Mock provider** - Test without Google API  
✅ **Backward compatible** - Single-user mode still works  
✅ **Production ready** - Security, performance, monitoring considered

**Next Steps**:

1. Run migrations
2. Configure OAuth (multi-user) or env vars (single-user)
3. Test with `/applications/extract` endpoint
4. Connect users via `/oauth/google/init`
5. Monitor confidence scores and adjust heuristics

**Support**:

- Check troubleshooting section
- Review test files for examples
- See GMAIL_INTEGRATION.md for single-user setup

---

**Last Updated**: October 9, 2025  
**Version**: 2.0  
**Author**: ApplyLens Team
