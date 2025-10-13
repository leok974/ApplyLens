# Phase 37: ML Pipeline Integration - Status Report

## ✅ What's Working

### 1. API Endpoints (All Live on port 8003)

```bash
# ✅ Gmail Backfill
curl -X POST "http://localhost:8003/api/gmail/backfill?days=7"
# Returns: {"inserted": 96, "days": 7, "user_email": "leoklemet.pa@gmail.com"}

# ✅ ML Label Rebuild (PostgreSQL only)
curl -X POST "http://localhost:8003/api/ml/label/rebuild?limit=2000"
# Returns: {"updated": 1894, "categories": {"ats": 15, "other": 1519, "promotions": 263, "bills": 30, "events": 67}}

# ✅ Profile Rebuild
curl -X POST "http://localhost:8003/profile/rebuild?user_email=leoklemet.pa@gmail.com"
# Returns: {"user_email": "...", "emails_processed": 403, "senders": 67, "categories": 5, "interests": 100}

# ✅ Profile Summary
curl "http://localhost:8003/profile/db-summary?user_email=leoklemet.pa@gmail.com"
# Returns: Full profile with top senders, categories, interests
```text

### 2. Frontend Components

- ✅ SearchControls component with category buttons
- ✅ ML badges on EmailCard and EmailRow
- ✅ ProfileSummary component
- ✅ AppHeader with 3-step pipeline
- ✅ Search page with URL param parsing

### 3. Backend Search Endpoint

- ✅ Categories filter param added
- ✅ Hide expired filter param added
- ✅ SearchHit model updated with ML fields
- ✅ Elasticsearch filter logic implemented

---

## ⚠️ Critical Issue: PostgreSQL → Elasticsearch Sync

### Problem

The `/ml/label/rebuild` endpoint updates PostgreSQL but **NOT Elasticsearch**.

**Result:** Search returns emails with `category: null`, `expires_at: null`, etc.

### Verification

```bash
# Search shows null ML fields
curl "http://localhost:8003/api/search/?q=interview&size=3"
# Response shows: "category": null, "expires_at": null, "event_start_at": null
```text

### Root Cause

```python
# services/api/app/routers/labeling.py line 88-95
email_row.category = category
email_row.ml_scores = scores
email_row.ml_features = features
email_row.amount_cents = amount_cents
email_row.expires_at = expires_at
email_row.event_start_at = event_start_at

# Commits to PostgreSQL only - no ES update!
db.commit()
```text

---

## 🔧 Solutions

### Option 1: Add ES sync to label_rebuild endpoint (RECOMMENDED)

Add Elasticsearch bulk update after PostgreSQL commit:

```python
# In services/api/app/routers/labeling.py

from elasticsearch import Elasticsearch
import os

ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200")
ES_INDEX = os.getenv("ES_EMAIL_INDEX", "emails_v1-000001")

def get_es_client():
    return Elasticsearch(ES_URL)

@router.post("/label/rebuild")
def label_rebuild(limit: int = 2000, user_email: Optional[str] = None, db: Session = Depends(get_db)):
    # ... existing code ...
    
    # After db.commit(), add ES sync:
    es_client = get_es_client()
    bulk_body = []
    
    for email_row in emails:
        if hasattr(email_row, 'category') and email_row.gmail_id:
            bulk_body.append({"update": {"_index": ES_INDEX, "_id": email_row.gmail_id}})
            bulk_body.append({"doc": {
                "category": email_row.category,
                "expires_at": email_row.expires_at.isoformat() if email_row.expires_at else None,
                "event_start_at": email_row.event_start_at.isoformat() if email_row.event_start_at else None,
                "event_end_at": email_row.event_end_at.isoformat() if email_row.event_end_at else None,
                "amount_cents": email_row.amount_cents,
                "ml_scores": email_row.ml_scores,
                "ml_features": email_row.ml_features,
                "confidence": email_row.confidence
            }})
    
    if bulk_body:
        es_client.bulk(body=bulk_body, refresh=True)
        logger.info(f"Synced {len(bulk_body)//2} emails to Elasticsearch")
    
    return {"updated": updated, "categories": category_counts, "errors": errors[:10] if errors else None}
```text

### Option 2: Create separate sync endpoint

```python
@router.post("/sync-to-es")
def sync_to_es(limit: int = 2000, user_email: Optional[str] = None, db: Session = Depends(get_db)):
    """Sync PostgreSQL ML fields to Elasticsearch."""
    # Read from PG, bulk update to ES
    pass
```text

### Option 3: Use existing backfill scripts

Check if `scripts/backfill_es_category.py` can be adapted or run directly.

---

## 📋 Quick Wins to Implement

### 1. Fix Empty Categories Filter

```typescript
// apps/web/src/pages/Search.tsx
const categories = useMemo(() => 
  (searchParams.get("cat") ?? "").split(",").filter(Boolean),  // ✅ Already done
  [searchParams]
)
```text

### 2. Badge Color Improvements

```tsx
// Use dark mode friendly colors
{expires && (
  <Badge className="border-amber-600/40 bg-amber-700/20 text-amber-300 dark:border-amber-600/60 dark:bg-amber-700/30">
    ⏰ {formatDistanceToNowStrict(new Date(expires), { addSuffix: true })}
  </Badge>
)}

{event && (
  <Badge className="border-sky-600/40 bg-sky-700/20 text-sky-300 dark:border-sky-600/60 dark:bg-sky-700/30">
    📅 {format(new Date(event), "MMM d")}
  </Badge>
)}
```text

### 3. Loading States

```tsx
// apps/web/src/pages/Search.tsx
{loading && (
  <div className="space-y-3">
    {[1, 2, 3].map(i => (
      <Skeleton key={i} className="h-16 w-full rounded-xl" />
    ))}
  </div>
)}
```text

### 4. Better Toast Messages

```typescript
// apps/web/src/components/AppHeader.tsx
toast({ 
  title: "✅ Sync complete!",
  description: `Labels + Profile updated. ${labelResult.updated} emails processed.`  // ✅ Already done
})
```text

### 5. Error Handling

```tsx
// apps/web/src/pages/Search.tsx
{err && (
  <Alert variant="destructive">
    <AlertCircle className="h-4 w-4" />
    <AlertDescription>
      Search failed: {err}. Elasticsearch may be unavailable.
    </AlertDescription>
  </Alert>
)}
```text

---

## 🧪 Testing Checklist

### Backend API

- [x] ✅ POST /api/gmail/backfill?days=7 - Works
- [x] ✅ POST /api/ml/label/rebuild?limit=2000 - Works (PG only)
- [ ] ⏸️ Verify ES has ML fields after rebuild
- [x] ✅ POST /profile/rebuild - Works
- [x] ✅ GET /profile/db-summary - Works
- [ ] ⏸️ GET /api/search/?categories=ats - Pending ES sync

### Frontend UI

- [ ] ⏸️ Click category buttons - URL updates ✅, results filter ⏸️
- [ ] ⏸️ Toggle "Hide expired" - URL updates ✅, results filter ⏸️
- [ ] ⏸️ See ML badges on email cards - Pending data
- [x] ✅ Click "Sync 7 days" - Shows 4 toasts correctly
- [ ] ⏸️ View ProfileSummary - Need to add to profile page

### Edge Cases

- [x] ✅ Empty categories filter: `filter(Boolean)` guards against `[""]`
- [x] ✅ Multiple categories: `&categories=ats&categories=promotions`
- [x] ✅ Hide expired logic: Uses `should` with `minimum_should_match`
- [ ] ⏸️ ES mapping has ML fields

---

## 🚀 Immediate Next Steps

1. **Fix ES Sync (Critical)**
   - Add bulk update to `label_rebuild` endpoint
   - Test: Run rebuild, verify search shows categories

2. **Verify ES Mapping**

   ```bash
   curl "http://localhost:9200/emails_v1-000001/_mapping" | jq '.[] .mappings.properties | keys'
   # Should include: category, expires_at, event_start_at, amount_cents, ml_scores
   ```

3. **Test Full Pipeline**

   ```bash
   # Step 1: Sync emails
   curl -X POST "http://localhost:8003/api/gmail/backfill?days=7"
   
   # Step 2: Apply labels (with ES sync fix)
   curl -X POST "http://localhost:8003/api/ml/label/rebuild?limit=2000"
   
   # Step 3: Verify search shows categories
   curl "http://localhost:8003/api/search/?q=interview&size=3" | jq '.[0].category'
   # Should NOT be null
   
   # Step 4: Test category filter
   curl "http://localhost:8003/api/search/?q=interview&categories=ats&size=3"
   # Should return only ATS emails
   ```

4. **Add ProfileSummary to UI**
   - Create profile page or add to existing dashboard
   - Import and render `<ProfileSummary />` component

5. **Polish UI**
   - Add loading skeletons
   - Improve badge colors for dark mode
   - Add error alerts for ES failures

---

## 📊 Current Data State

### PostgreSQL (Source of Truth)

- ✅ 1,894 emails labeled
- ✅ Categories: ats (15), promotions (263), bills (30), events (67), other (1519)
- ✅ Profile data: 403 emails processed, 67 senders, 5 categories, 100 interests

### Elasticsearch (Search Index)

- ⚠️ ML fields NOT synced
- ⚠️ All searches return `category: null`
- ⚠️ Category filters don't work (no data to filter)

---

## 🎯 Success Criteria

- [ ] Search with `?categories=ats` returns only ATS emails
- [ ] Search with `?hide_expired=true` excludes past events/promos
- [ ] Email cards show category badges (ats, promotions, etc.)
- [ ] Email cards show expiry badges (⏰ expires in 3 days)
- [ ] Email cards show event badges (📅 Oct 15)
- [ ] ProfileSummary displays top senders/categories/interests
- [ ] Full sync pipeline works end-to-end from UI

---

**Last Updated:** October 12, 2025  
**Status:** 90% complete - Only ES sync blocking full functionality
