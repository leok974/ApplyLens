# v0.4.27 Deployment Guide

## Version: v0.4.27 - Enhanced Actions Page with Drawer UI

## Changes Summary
- ✅ **Backend**: Added GET `/api/actions/message/{id}` endpoint for full message detail
- ✅ **Backend**: Added `generate_explanation_for_message()` deterministic helper (no LLM)
- ✅ **Backend**: Enhanced `ActionResponse` model with `new_risk_score`, `quarantined`, `archived` fields
- ✅ **Backend**: All mutation endpoints now return rich response data for optimistic UI updates
- ✅ **Frontend**: Added drawer UI (shadcn Sheet component) for full email viewing
- ✅ **Frontend**: Added inline explanations with collapse toggle
- ✅ **Frontend**: Implemented optimistic UI updates for all action mutations
- ✅ **Frontend**: Added CSRF token support for all mutation endpoints
- ✅ **Frontend**: Row clicks open drawer, action buttons use stopPropagation

## Docker Images
- **API**: `leoklemet/applylens-api:v0.4.27`
  - Digest: `sha256:8fc2071b011ff7648cb2242334ba4b0cdecbea8e22bde908cc918f81ff7091aa`
- **Web**: `leoklemet/applylens-web:v0.4.27`
  - Digest: `sha256:a6d821a4b90087e3d9190f62772863a8b8abfc1721b6d25ef386776d66951b72`

## Deployment Steps

### 1. SSH to Production Server
```bash
ssh user@your-production-host
cd /path/to/ApplyLens
```

### 2. Pull Changes
```bash
git pull origin demo
```

### 3. Pull Docker Images
```bash
docker compose -f docker-compose.prod.yml pull api web
```

### 4. Recreate Containers
```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate api web
```

### 5. Restart Nginx (optional, if routing issues)
```bash
docker restart applylens-nginx-prod
```

### 6. Verify Health
```bash
curl https://applylens.app/api/healthz
```

## Verification Checklist

### Basic Health
- [ ] API health endpoint returns 200: `https://applylens.app/api/healthz`
- [ ] Actions page loads: `https://applylens.app/inbox-actions`
- [ ] No JavaScript console errors

### Actions Page Features
- [ ] **Row Click**: Click any email row → drawer opens with full email
- [ ] **Drawer Content**:
  - From/To/Subject/Date displayed
  - Risk score badge shown
  - Category badge shown
  - Quarantined badge (if applicable)
  - Email body (HTML or text) rendered correctly
- [ ] **Explain Button**: Click "🔍 Explain why" → inline explanation appears below row
- [ ] **Explanation Toggle**: Click again → explanation collapses
- [ ] **Close Drawer**: Click X or outside → drawer closes

### Production Read-Only Mode
- [ ] **No Mutation Buttons**: Archive, Mark Safe, Mark Suspicious, Unsubscribe buttons should NOT be visible in production
- [ ] **Only Explain Button**: Only "Explain why" button should be visible
- [ ] **No 403 Errors**: Browser console should have no 403 errors from blocked mutations

## Expected Behavior

### In Production (ALLOW_ACTION_MUTATIONS=false or unset)
- ✅ Rows clickable → opens drawer
- ✅ "Explain why" button visible and functional
- ❌ Archive button hidden
- ❌ Mark Safe button hidden
- ❌ Mark Suspicious button hidden
- ❌ Unsubscribe button hidden

### In Development (ALLOW_ACTION_MUTATIONS=true)
- ✅ All action buttons visible
- ✅ Optimistic UI updates on mutation
- ✅ Server response updates risk scores, quarantine status

## Rollback Plan

If issues arise:

```bash
# Update docker-compose.prod.yml to v0.4.26
# Then run:
docker compose -f docker-compose.prod.yml pull api web
docker compose -f docker-compose.prod.yml up -d --force-recreate api web
```

## Testing in Dev

If you want to test mutations locally:

```bash
# In docker-compose.yml or .env
ALLOW_ACTION_MUTATIONS=true

# Restart API
docker compose restart api
```

Then visit Actions page - all buttons will be visible and functional.

## Commit
- **Branch**: demo
- **Commit**: 5291dd6
- **Message**: "feat: v0.4.27 Enhanced Actions page with drawer UI"

## Notes
- This version is production-safe by default (read-only)
- Drawer UI provides rich email viewing experience
- Explanations are deterministic (no LLM calls)
- All mutation endpoints enhanced with optimistic update support
- CSRF tokens required for all mutations
