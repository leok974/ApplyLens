# Gmail OAuth & Backfill Integration - Setup Guide

## Overview

ApplyLens now supports Gmail OAuth authentication and automated email backfill with intelligent heuristic labeling for job search emails.

## Features

✅ Google OAuth 2.0 authentication flow
✅ Secure token storage and refresh
✅ Gmail API integration with message parsing
✅ HTML-to-text conversion with BeautifulSoup
✅ Heuristic email labeling (interview, offer, rejection, application_receipt, newsletter_ads)
✅ Bulk Elasticsearch indexing with synonym support
✅ Automatic token refresh handling

## Prerequisites

1. Google Cloud Project with Gmail API enabled
2. OAuth 2.0 Client ID (Desktop Application type)
3. Downloaded OAuth credentials JSON file

## Setup Instructions

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the **Gmail API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client ID"
   - Application type: **Desktop app**
   - Name: "ApplyLens Gmail"
   - Click "Create"
5. Download the JSON file
6. Save it as `google.json` in `infra/secrets/` directory

### 2. Configure Redirect URI

In the Google Cloud Console, add the following redirect URI to your OAuth client:

```
http://localhost:8003/auth/google/callback
```

*Note: Adjust the port if you changed API_PORT in .env*

### 3. Update Environment Variables

The `.env` file has been pre-configured with these variables:

```bash
# Gmail OAuth Configuration
GOOGLE_CREDENTIALS=/secrets/google.json
GOOGLE_OAUTH_SCOPES=https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email openid
OAUTH_STATE_SECRET=change_me_to_a_random_32_character_or_longer_string
OAUTH_REDIRECT_URI=http://localhost:8003/auth/google/callback

# Elasticsearch index name for Gmail emails
ELASTICSEARCH_INDEX=gmail_emails
```

**Important:** Change `OAUTH_STATE_SECRET` to a random string (32+ characters) for production use.

### 4. Start Services

```bash
docker compose -f infra/docker-compose.yml up -d
```

The API container will automatically:

- Install Gmail dependencies (google-auth, google-api-python-client, beautifulsoup4, bleach)
- Apply database migrations (OAuth tokens table, Gmail fields)
- Create Elasticsearch index with Gmail mappings

### 5. Test the Setup

Check API health:

```bash
curl http://localhost:8003/healthz
```

View API documentation:

```bash
open http://localhost:8003/docs
```

## Usage

### Authentication Flow

#### 1. Initiate OAuth Login

Visit in your browser:

```
http://localhost:8003/auth/google/login
```

This will redirect you to Google's consent screen.

#### 2. Grant Permissions

- Select your Google account
- Review permissions (Gmail read-only access)
- Click "Allow"

#### 3. Callback Redirect

After authentication, you'll be redirected to:

```
http://localhost:5175/inbox?connected=google
```

The OAuth token is now stored in the database.

### Backfill Gmail Messages

#### Basic Backfill (last 60 days)

```bash
curl -X POST "http://localhost:8003/gmail/backfill?days=60&user_email=your.email@gmail.com"
```

Response:

```json
{
  "inserted": 243,
  "days": 60,
  "user_email": "your.email@gmail.com"
}
```

#### Custom Time Range

Backfill last 30 days:

```bash
curl -X POST "http://localhost:8003/gmail/backfill?days=30&user_email=your.email@gmail.com"
```

Backfill up to 1 year:

```bash
curl -X POST "http://localhost:8003/gmail/backfill?days=365&user_email=your.email@gmail.com"
```

### Search Gmail Messages

#### Basic Search

```bash
curl "http://localhost:8003/search?q=Interview"
```

#### Label-Based Queries

Search for interviews:

```bash
curl "http://localhost:8003/search?q=interview"
```

Search for offers:

```bash
curl "http://localhost:8003/search?q=offer"
```

Search for application receipts:

```bash
curl "http://localhost:8003/search?q=application+received"
```

## Heuristic Labels

The system automatically applies these labels based on content analysis:

| Label | Trigger Keywords | Use Case |
|-------|------------------|----------|
| `interview` | interview, phone screen, onsite, screening, call | Identifies interview invitations |
| `offer` | offer, offer letter, acceptance | Identifies job offers |
| `rejection` | not selected, unfortunately, regret to inform, rejection | Identifies rejections |
| `application_receipt` | application received, submitted, confirmation | Identifies application confirmations |
| `newsletter_ads` | unsubscribe, noreply, newsletter | Identifies promotional emails |

## Database Schema

### OAuthToken Table

```sql
CREATE TABLE oauth_tokens (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(32) NOT NULL,           -- "google"
    user_email VARCHAR(320) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_uri TEXT NOT NULL,
    client_id TEXT NOT NULL,
    client_secret TEXT NOT NULL,
    scopes TEXT NOT NULL,
    expiry TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX ix_oauth_tokens_provider ON oauth_tokens(provider);
CREATE INDEX ix_oauth_tokens_user_email ON oauth_tokens(user_email);
```

### Email Table (Gmail Fields)

New columns added:

- `gmail_id` (VARCHAR(128), unique) - Gmail message ID
- `labels` (ARRAY) - Gmail labels from API
- `label_heuristics` (ARRAY) - Auto-detected labels
- `raw` (JSON) - Full Gmail API response

## Elasticsearch Index

Index name: `gmail_emails`

Key mappings:

```json
{
  "gmail_id": {"type": "keyword"},
  "sender": {"type": "keyword"},
  "recipient": {"type": "keyword"},
  "subject": {"type": "text", "analyzer": "applylens_text"},
  "body_text": {"type": "text", "analyzer": "applylens_text"},
  "labels": {"type": "keyword"},
  "label_heuristics": {"type": "keyword"},
  "subject_suggest": {"type": "completion"},
  "received_at": {"type": "date"}
}
```

## API Endpoints

### OAuth

- `GET /auth/google/login` - Initiate OAuth flow
- `GET /auth/google/callback` - OAuth callback handler

### Gmail Operations

- `POST /gmail/backfill` - Backfill messages from Gmail
  - Query params:
    - `days` (1-365): Number of days to backfill
    - `user_email`: User's Gmail address

### Search

- `GET /search` - Search indexed emails
  - Query params:
    - `q`: Search query
    - `size`: Results per page (default: 20)

## Testing

### Run Unit Tests

```bash
docker compose -f infra/docker-compose.yml exec api pytest tests/test_labeler.py -v
```

Expected output:

```
test_labeler.py::test_interview_detection PASSED
test_labeler.py::test_offer_detection PASSED
test_labeler.py::test_rejection_detection PASSED
test_labeler.py::test_application_receipt_detection PASSED
test_labeler.py::test_newsletter_detection PASSED
```

### Manual Testing

1. **Authenticate:**

   ```bash
   open http://localhost:8003/auth/google/login
   ```

2. **Backfill emails:**

   ```bash
   curl -X POST "http://localhost:8003/gmail/backfill?days=7&user_email=your@gmail.com"
   ```

3. **Search:**

   ```bash
   curl "http://localhost:8003/search?q=interview"
   ```

4. **Check Elasticsearch:**

   ```bash
   curl http://localhost:9200/gmail_emails/_count
   ```

## Security Considerations

### ⚠️ Important Security Notes

1. **Never commit `google.json` to git** - It's already in `.gitignore`
2. **Change `OAUTH_STATE_SECRET`** - Use a cryptographically random string
3. **Use HTTPS in production** - Update `OAUTH_REDIRECT_URI` accordingly
4. **Restrict OAuth scopes** - Only request necessary permissions
5. **Token encryption** - Consider encrypting tokens at rest in production

### Production Deployment

For production, update these settings:

```bash
# Production OAuth redirect (HTTPS)
OAUTH_REDIRECT_URI=https://yourdomain.com/auth/google/callback

# Strong random secret (generate with: openssl rand -base64 32)
OAUTH_STATE_SECRET=$(openssl rand -base64 32)
```

## Troubleshooting

### "No module named 'google_auth_oauthlib'"

Rebuild API container:

```bash
docker compose -f infra/docker-compose.yml build --no-cache api
docker compose -f infra/docker-compose.yml up -d api
```

### "redirect_uri_mismatch" Error

Ensure redirect URI in Google Console matches exactly:

```
http://localhost:8003/auth/google/callback
```

### "Invalid state" Error

Check that `OAUTH_STATE_SECRET` is set and consistent.

### Token Refresh Issues

Tokens are automatically refreshed. If issues persist:

```sql
-- Clear tokens from database
DELETE FROM oauth_tokens WHERE provider = 'google';
```

Then re-authenticate via `/auth/google/login`.

### Elasticsearch Index Issues

Recreate index:

```bash
# Set ES_RECREATE_ON_START=true in .env
docker compose -f infra/docker-compose.yml restart api
```

## Development

### File Structure

```
services/api/app/
├── auth_google.py        # OAuth flow handlers
├── gmail_service.py      # Gmail API integration
├── routes_gmail.py       # Gmail endpoints
├── models.py             # OAuthToken, Email models
├── es.py                 # Elasticsearch config
└── main.py               # FastAPI app with routes

tests/
└── test_labeler.py       # Heuristic labeling tests

infra/
├── secrets/
│   ├── README.md         # Setup instructions
│   └── google.json       # OAuth credentials (gitignored)
└── docker-compose.yml    # Updated with secrets mount
```

### Adding New Label Heuristics

Edit `services/api/app/gmail_service.py`:

```python
# Add regex pattern
MY_PATTERN = re.compile(r"(?i)\bmy pattern\b")

# Add to derive_labels function
def derive_labels(sender: str, subject: str, body: str) -> List[str]:
    labels = []
    text = " ".join([subject or "", body or ""])
    
    if MY_PATTERN.search(text):
        labels.append("my_label")
    
    # ... existing patterns
    return list(set(labels))
```

## Next Steps

1. **Frontend Integration** - Add Gmail connect button to UI
2. **Multi-User Support** - Implement user session management
3. **Scheduled Sync** - Add cron job for periodic backfill
4. **Advanced Labeling** - Use ML models for better classification
5. **Email Actions** - Add archive, mark read, delete functionality

## Support

For issues or questions:

- Check logs: `docker compose -f infra/docker-compose.yml logs api`
- View API docs: <http://localhost:8003/docs>
- Test endpoints with Swagger UI

## License

Part of the ApplyLens project.
