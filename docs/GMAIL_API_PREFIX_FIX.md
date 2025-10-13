# Gmail API Routes - Prefix Fix

**Date**: October 12, 2025  
**Issue**: `/api/gmail/status` returning 404  
**Status**: ✅ Fixed

---

## Problem

The frontend was calling `/api/gmail/status` but the backend had registered the Gmail router without the `/api` prefix, making the route available at `/gmail/status` instead.

**Error in browser console**:

```
GET http://localhost:5175/api/gmail/status 404 (Not Found)
Failed to fetch Gmail status
```

---

## Root Cause

In `services/api/app/main.py`, the `routes_gmail.router` was included without the `/api` prefix:

```python
# ❌ Before (incorrect)
app.include_router(routes_gmail.router)
```

This made the routes available at:

- `/gmail/status`
- `/gmail/inbox`
- `/gmail/backfill`

But the frontend expected them at:

- `/api/gmail/status`
- `/api/gmail/inbox`
- `/api/gmail/backfill`

---

## Solution

Added the `/api` prefix when including the `routes_gmail.router`:

```python
# ✅ After (correct)
app.include_router(routes_gmail.router, prefix="/api")
```

**File changed**: `services/api/app/main.py` (line 67)

---

## Gmail Endpoints

All Gmail endpoints are now accessible under `/api/gmail/`:

### 1. GET `/api/gmail/status`

**Description**: Check if user has connected their Gmail account

**Query Parameters**:

- `user_email` (optional) - User email (defaults to env `DEFAULT_USER_EMAIL`)

**Response**:

```json
{
  "connected": true,
  "user_email": "user@example.com",
  "provider": "google",
  "has_refresh_token": true,
  "total": 1868
}
```

**Test**:

```bash
curl "http://localhost:8003/api/gmail/status"
```

---

### 2. GET `/api/gmail/inbox`

**Description**: Get paginated list of Gmail emails from database

**Query Parameters**:

- `page` (default: 1) - Page number (≥1)
- `limit` (default: 50) - Results per page (1-200)
- `label_filter` (optional) - Filter by label_heuristics
- `user_email` (optional) - User email

**Response**:

```json
{
  "emails": [
    {
      "id": 1857,
      "gmail_id": "test_gmail_id_3",
      "thread_id": "test_thread_B",
      "subject": "Re: Application confirmation",
      "body_preview": "Interview scheduled",
      "sender": "jobs@example.com",
      "recipient": "me@example.com",
      "received_at": "2025-10-01T10:00:00",
      "labels": ["INBOX", "UNREAD"],
      "label_heuristics": ["interview"],
      "company": "Example Inc",
      "role": "Software Engineer",
      "source": "greenhouse",
      "application_id": 2
    }
  ],
  "total": 1868,
  "page": 1,
  "limit": 50
}
```

**Test**:

```bash
curl "http://localhost:8003/api/gmail/inbox?page=1&limit=10"
```

---

### 3. POST `/api/gmail/backfill`

**Description**: Backfill Gmail messages from the last N days

**Query Parameters**:

- `days` (default: 60) - Number of days to backfill (1-365)
- `user_email` (optional) - User email

**Rate Limit**: 60 seconds between requests

**Response**:

```json
{
  "inserted": 150,
  "days": 60,
  "user_email": "user@example.com"
}
```

**Test**:

```bash
curl -X POST "http://localhost:8003/api/gmail/backfill?days=30"
```

---

## Verification

All endpoints tested and working:

✅ **Direct API access** (port 8003):

```bash
curl "http://localhost:8003/api/gmail/status"
curl "http://localhost:8003/api/gmail/inbox?page=1&limit=2"
```

✅ **Through Vite proxy** (port 5175):

```bash
curl "http://localhost:5175/api/gmail/status"
curl "http://localhost:5175/api/gmail/inbox?page=1&limit=2"
```

---

## Frontend Integration

The frontend (`apps/web/src/lib/api.ts`) correctly calls all endpoints with `/api` prefix:

```typescript
// Gmail status
export async function getGmailStatus(userEmail?: string): Promise<GmailConnectionStatus> {
  let url = '/api/gmail/status'
  if (userEmail) {
    url += `?user_email=${encodeURIComponent(userEmail)}`
  }
  const r = await fetch(url)
  if (!r.ok) throw new Error('Failed to fetch Gmail status')
  return r.json()
}

// Gmail inbox
export async function getGmailInbox(page = 1, limit = 50, labelFilter?: string): Promise<GmailInboxResponse> {
  let url = `/api/gmail/inbox?page=${page}&limit=${limit}`
  if (labelFilter) url += `&label_filter=${encodeURIComponent(labelFilter)}`
  const r = await fetch(url)
  if (!r.ok) throw new Error('Failed to fetch Gmail inbox')
  return r.json()
}

// Gmail backfill
export async function backfillGmail(days = 60): Promise<BackfillResponse> {
  let url = `/api/gmail/backfill?days=${days}`
  const r = await fetch(url, { method: 'POST' })
  if (!r.ok) throw new Error('Failed to backfill Gmail')
  return r.json()
}
```

---

## Other Routes with `/api` Prefix

The following routers also use the `/api` prefix:

```python
# main.py
app.include_router(applications.router, prefix="/api")  # /api/applications
app.include_router(routes_gmail.router, prefix="/api")  # /api/gmail (fixed)
```

**Routes without `/api` prefix** (intentional):

- `auth_google.router` - OAuth endpoints at `/google/auth`, `/google/callback`
- `oauth_google.router` - OAuth endpoints
- `emails.router` - Legacy endpoints at `/emails`
- `search.router` - Search endpoints at `/search`
- `suggest.router` - Suggest endpoints at `/suggest`
- `routes_extract.router` - Extract endpoints

---

## Deployment

**1. API restart**:

```bash
docker compose restart api
```

**2. No frontend changes needed** - Already using correct paths

**3. Verify in browser**:

- Open <http://localhost:5175/inbox>
- Check console - no 404 errors for `/api/gmail/status`

---

## Related Files

- `services/api/app/main.py` - Router registration (fixed)
- `services/api/app/routes_gmail.py` - Gmail endpoints implementation
- `apps/web/src/lib/api.ts` - Frontend API client
- `apps/web/src/pages/Inbox.tsx` - Uses `getGmailStatus()`

---

**Status**: ✅ Fixed and tested  
**Impact**: Gmail status checks now work in Inbox page  
**Breaking Changes**: None - frontend already expected `/api` prefix
