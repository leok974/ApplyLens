# Actions Page Implementation - v0.4.26

## Summary

Successfully implemented full Actions page functionality with real backend endpoints per user specification.

## Changes Made

### Backend (Python/FastAPI)

**1. New File: `services/api/app/routers/inbox_actions.py`**
- Created dedicated router for inbox actions
- Implemented all required endpoints:
  - `GET /api/actions/inbox` - Returns actionable emails (promotions, bulk, risky, unread)
  - `POST /api/actions/explain` - Explains why email needs action
  - `POST /api/actions/mark_safe` - Lowers risk score, clears quarantine
  - `POST /api/actions/mark_suspicious` - Raises risk score to 95, quarantines
  - `POST /api/actions/archive` - Adds ARCHIVED label
  - `POST /api/actions/unsubscribe` - Marks sender as muted

- Production-safe features:
  - `ALLOW_ACTION_MUTATIONS` env var check (defaults to true)
  - Returns 403 in production if mutations disabled
  - Graceful ES fallback (returns empty list if ES unavailable)
  - CSRF protection via FastAPI dependency injection

- Smart categorization:
  - Emails categorized as: Suspicious, Promotions, Updates, Forums, Spam, Unread, Other
  - Risk-based signals (high/medium/low)
  - Label-based signals (Gmail categories, bulk patterns, no-reply senders)
  - Conditional `allowed_actions` list based on environment

**2. Updated: `services/api/app/main.py`**
- Registered `inbox_actions` router
- Mounts at `/api/actions/*` prefix

### Frontend (React/TypeScript)

**1. Updated: `apps/web/src/lib/api.ts`**
- Added new types:
  - `ActionReason` - category, signals, risk_score, quarantined
  - `ActionRow` - full email row with allowed_actions
  - `ExplainActionResponse` - explanation summary

- Added new API functions:
  - `fetchActionsInbox()` - GET /api/actions/inbox
  - `explainAction(message_id)` - POST /api/actions/explain
  - `inboxActions` object with: markSafe, markSuspicious, archive, unsubscribe

**2. Replaced: `apps/web/src/components/InboxWithActions.tsx`**
- Complete rewrite to use new endpoints
- Features:
  - Fetches from `/api/actions/inbox` on mount
  - Conditional button rendering based on `allowed_actions[]`
  - Inline explanations after "Explain why" click
  - Loading states per email row
  - Toast notifications for success/error
  - Graceful error handling (detects read-only mode)
  - Auto-refresh inbox after successful actions
  - Clean empty state message

## Testing

### Local Development Testing
1. Start API: `cd services/api && python -m app.main`
2. Start Web: `cd apps/web && npm run dev`
3. Visit: http://localhost:5176/inbox-actions
4. Test all buttons (Archive, Safe, Suspicious, Unsub)
5. Test "Explain why" functionality
6. Verify mutations work when `ALLOW_ACTION_MUTATIONS=true`

### Production Testing Plan
1. Build images: `docker build -t leoklemet/applylens-api:v0.4.26 services/api`
2. Build images: `docker build -t leoklemet/applylens-web:v0.4.26 apps/web`
3. Push to Docker Hub
4. Update `docker-compose.prod.yml` to v0.4.26
5. Deploy: `docker compose -f docker-compose.prod.yml up -d --force-recreate api web`
6. Restart nginx: `docker restart applylens-nginx-prod`
7. Test at https://applylens.app/inbox-actions
8. Verify read-only mode (mutations should return 403 in prod until enabled)

## Environment Variables

```bash
# Development (default)
ALLOW_ACTION_MUTATIONS=true

# Production (recommended until fully tested)
ALLOW_ACTION_MUTATIONS=false
```

## API Response Examples

### GET /api/actions/inbox
```json
[
  {
    "message_id": "18f3c2e1b8a9d4f0",
    "from_name": "LinkedIn",
    "from_email": "messages-noreply@linkedin.com",
    "subject": "You have 3 new connection requests",
    "received_at": "2024-01-15T10:30:00Z",
    "labels": ["CATEGORY_UPDATES", "UNREAD"],
    "reason": {
      "category": "Updates",
      "signals": [
        "Labeled PROMOTIONS by Gmail",
        "Automated sender (no-reply)",
        "Unread email"
      ],
      "risk_score": 15,
      "quarantined": false
    },
    "allowed_actions": ["archive", "mark_safe", "mark_suspicious", "unsubscribe", "explain"]
  }
]
```

### POST /api/actions/explain
Request:
```json
{
  "message_id": "18f3c2e1b8a9d4f0"
}
```

Response:
```json
{
  "summary": "This email is categorized as Updates, because it labeled PROMOTIONS by Gmail and automated sender (no-reply). Risk score is low (15/100), so it's likely safe but noisy."
}
```

### POST /api/actions/mark_safe
Request:
```json
{
  "message_id": "18f3c2e1b8a9d4f0"
}
```

Response:
```json
{
  "ok": true
}
```

## Next Steps

1. **Deploy to Production** - Build and deploy v0.4.26
2. **Playwright Tests** - Create e2e tests as specified
3. **Monitor Usage** - Track which actions are most used
4. **Enable Mutations** - Set `ALLOW_ACTION_MUTATIONS=true` in prod after testing
5. **Future Enhancements**:
   - Bulk actions (select multiple emails)
   - Undo functionality
   - Real unsubscribe link clicking (not just marking)
   - Smart filters (show only high-risk, only promotions, etc.)
   - Action history/audit log view

## Known Limitations

1. **Elasticsearch Required** - If ES is unavailable, inbox returns empty list
2. **No Gmail Sync** - Actions only modify local ES index, not Gmail itself
3. **Unsubscribe is Passive** - Doesn't actually click unsubscribe links yet
4. **No Bulk Selection** - Can only act on one email at a time
5. **No Undo** - Actions are immediate and permanent

## Production Safety

- ✅ Graceful ES error handling
- ✅ User authentication required (via `get_current_user_email`)
- ✅ CSRF protection on all POST endpoints
- ✅ Environment-based mutation control
- ✅ Conditional button rendering (no buttons if action not allowed)
- ✅ Informative error messages
- ✅ Production read-only mode support
