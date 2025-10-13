# Gmail Integration - Quick Reference

## ⚡ Quick Setup (5 minutes)

### 1. Get OAuth Credentials

```bash
# Visit: https://console.cloud.google.com/
# Create project → Enable Gmail API → Create OAuth client (Desktop app)
# Download credentials.json
```

### 2. Generate Refresh Token

```bash
cd services/api

# Install tool
pip install google-auth-oauthlib

# Generate token (opens browser)
python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json',
    scopes=['https://www.googleapis.com/auth/gmail.readonly']
)
creds = flow.run_local_server(port=0)
print('GMAIL_REFRESH_TOKEN=' + creds.refresh_token)
"
```

### 3. Configure Environment

```bash
# Create/edit .env
cat >> .env << EOF
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REFRESH_TOKEN=1//your-refresh-token
GMAIL_USER=your-email@gmail.com
EOF
```

### 4. Restart API

```bash
uvicorn app.main:app --reload --port 8003
```

## 🔥 Usage

### Test Extract Endpoint

```bash
# With Gmail thread ID (auto-fetch)
curl -X POST http://localhost:8003/api/applications/extract \
  -H "Content-Type: application/json" \
  -d '{"gmail_thread_id": "18f2a3b4c5d6e7f8"}'

# Response
{
  "company": "acme",
  "role": "Senior Engineer",
  "source": "Greenhouse",
  "source_confidence": 0.95,
  "debug": {
    "used_gmail": true,
    "from": "recruiter@acme.ai",
    "subject": "Application for Senior Engineer"
  }
}
```

### Test Backfill Endpoint

```bash
# Create application from Gmail thread
curl -X POST http://localhost:8003/api/applications/backfill-from-email \
  -H "Content-Type: application/json" \
  -d '{"gmail_thread_id": "18f2a3b4c5d6e7f8"}'

# Response
{
  "saved": {
    "id": 123,
    "company": "Acme Corp",
    "role": "Senior Engineer",
    "thread_id": "18f2a3b4c5d6e7f8",
    "source_confidence": 0.95
  },
  "extracted": { ... },
  "updated": false
}
```

## 🔍 Finding Thread IDs

### From Gmail Web

1. Open email in Gmail
2. Look at URL: `https://mail.google.com/mail/u/0/#inbox/18f2a3b4c5d6e7f8`
3. Thread ID = `18f2a3b4c5d6e7f8`

### From Python

```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

creds = Credentials(
    token=None,
    refresh_token="YOUR_REFRESH_TOKEN",
    token_uri="https://oauth2.googleapis.com/token",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET"
)

service = build('gmail', 'v1', credentials=creds)
results = service.users().messages().list(
    userId='me',
    q='from:recruiter@company.com'
).execute()

for msg in results.get('messages', []):
    print(msg['threadId'])
```

## 🎯 Environment Variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `GMAIL_CLIENT_ID` | Yes | `123-abc.apps.googleusercontent.com` | OAuth client ID |
| `GMAIL_CLIENT_SECRET` | Yes | `GOCSPX-abc123` | OAuth client secret |
| `GMAIL_REFRESH_TOKEN` | Yes | `1//abc123def456` | OAuth refresh token |
| `GMAIL_USER` | Yes | `you@gmail.com` | Gmail account to fetch from |

**All 4 must be set for Gmail integration to work.**

## ✅ Testing Checklist

```bash
# 1. Check env vars
env | grep GMAIL

# 2. Test extract (Gmail)
curl -X POST http://localhost:8003/api/applications/extract \
  -H "Content-Type: application/json" \
  -d '{"gmail_thread_id": "REAL_THREAD_ID"}'

# 3. Test extract (fallback)
curl -X POST http://localhost:8003/api/applications/extract \
  -H "Content-Type: application/json" \
  -d '{"subject": "Test", "from": "test@example.com", "text": "Test email"}'

# 4. Test backfill
curl -X POST http://localhost:8003/api/applications/backfill-from-email \
  -H "Content-Type: application/json" \
  -d '{"gmail_thread_id": "REAL_THREAD_ID"}'

# 5. Verify in database
sqlite3 your.db "SELECT * FROM applications WHERE thread_id='REAL_THREAD_ID'"
```

## 🚨 Troubleshooting

### "gmail_not_configured" Error

```bash
# Check env vars
env | grep GMAIL

# Ensure all 4 are set
export GMAIL_CLIENT_ID="..."
export GMAIL_CLIENT_SECRET="..."
export GMAIL_REFRESH_TOKEN="..."
export GMAIL_USER="you@gmail.com"

# Restart API
```

### "Invalid credentials" Error

```bash
# Regenerate refresh token
python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json',
    scopes=['https://www.googleapis.com/auth/gmail.readonly']
)
creds = flow.run_local_server(port=0)
print(creds.refresh_token)
"

# Update .env with new token
```

### "Thread not found" Error

- Verify thread ID is correct
- Check account has access to thread
- Ensure thread still exists (not deleted)

## 🎓 Key Concepts

### Graceful Fallback

If Gmail not configured or thread fetch fails, API uses request body:

```typescript
// Frontend sends both (safe!)
{
  "gmail_thread_id": "abc123",    // Try Gmail first
  "subject": "Fallback subject",  // Use if Gmail fails
  "from": "fallback@example.com",
  "text": "Fallback content"
}
```

### Latest Message

Gmail integration fetches the **latest message** in the thread (sorted by `internalDate`).

### MIME Parsing

- Prefers `text/plain` over `text/html`
- Decodes base64url (Gmail format)
- Flattens nested multipart structures
- Extracts all headers for heuristics

## 📊 Performance

| Operation | Latency | Quota Cost |
|-----------|---------|------------|
| Extract (Gmail) | ~300-500ms | 5 units |
| Extract (fallback) | ~50ms | 0 units |
| Backfill (Gmail) | ~400-600ms | 5 units |

**Gmail API Quotas**:

- 250 units/user/second
- 1 billion units/day
- `threads.get` = 5 units

## 🔐 Security

### Scope

- `https://www.googleapis.com/auth/gmail.readonly`
- **Cannot send or delete emails**

### Token Storage

- ✅ Environment variable (`.env`)
- ❌ Never in code or version control
- ✅ Can be revoked anytime

### Production

- Consider service account instead of user OAuth
- Rotate refresh tokens periodically
- Monitor API usage in Google Cloud Console

## 📦 Files Modified

### Backend

- ✅ `services/api/app/gmail.py` - Gmail client (new)
- ✅ `services/api/app/routes_applications.py` - Updated endpoints
- ✅ Environment variables required

### Frontend

- ✅ `apps/web/src/components/CreateFromEmailButton.tsx` - Sends `gmail_thread_id`
- No other changes needed

## 🚀 What's Different

### Before

```typescript
// Frontend had to pass full email content
{
  "subject": "...",
  "from": "...",
  "text": "...",
  "headers": { ... }
}
```

### After

```typescript
// Just pass thread ID (backend fetches automatically)
{
  "gmail_thread_id": "18f2a3b4c5d6e7f8"
}

// Fallback still works
{
  "subject": "...",  // Used if Gmail not configured
  "from": "..."
}
```

## 🎉 Benefits

1. **Less frontend code** - No need to parse email content
2. **Better accuracy** - Always gets latest message
3. **Graceful fallback** - Works without Gmail
4. **No breaking changes** - Old API calls still work
5. **Optional setup** - Configure only if needed

---

## 📖 Full Documentation

See `GMAIL_INTEGRATION.md` for complete details, OAuth setup, security considerations, and advanced usage.

**Setup Time**: 5-15 minutes  
**Breaking Changes**: None  
**Required**: No (optional feature)
