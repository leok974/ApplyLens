# Email Extraction - Quick Reference

## 🚀 Quick Start

### Start Development Environment

```bash
# Terminal 1: Start FastAPI backend
cd services/api
python -m uvicorn app.main:app --reload --port 8003

# Terminal 2: Start Vite frontend
cd apps/web
npm run dev
```text

### Access Points

- **Frontend**: <http://localhost:5175/tracker>
- **API Docs**: <http://localhost:8003/docs>
- **Extract Endpoint**: POST <http://localhost:8003/api/applications/extract>
- **Backfill Endpoint**: POST <http://localhost:8003/api/applications/backfill-from-email>

## 📋 API Reference

### POST `/api/applications/extract`

**Purpose**: Extract fields from email without saving

**Request**:

```json
{
  "subject": "Application for Senior Engineer",
  "from": "jane@acme.ai",
  "headers": {"List-Unsubscribe": "..."},
  "text": "Email body...",
  "html": "<html>..."
}
```text

**Response**:

```json
{
  "company": "acme",
  "role": "Senior Engineer",
  "source": "Greenhouse",
  "source_confidence": 0.95,
  "debug": { ... }
}
```text

**Confidence Levels**:

- `0.95`: Known ATS (Greenhouse, Lever, Workday)
- `0.6`: Mailing list
- `0.5`: Generic ESP
- `0.4`: Unknown

### POST `/api/applications/backfill-from-email`

**Purpose**: Extract AND save to database

**Request**:

```json
{
  "thread_id": "18f2a3b4c5d6e7f8",
  "subject": "Application for Senior Engineer",
  "from": "jane@acme.ai",
  "text": "Email body...",
  "headers": {}
}
```text

**Response**:

```json
{
  "saved": {
    "id": 123,
    "company": "Acme",
    "role": "Senior Engineer",
    "source": "Greenhouse",
    "source_confidence": 0.95,
    "status": "applied",
    "thread_id": "18f2a3b4c5d6e7f8"
  },
  "extracted": { ... },
  "updated": false
}
```text

**Logic**:

1. Try to find existing app by `thread_id`
2. If not found, try to match by `company` + `role`
3. If found, update only if new confidence is higher
4. If not found, create new application

## 🎨 Frontend Components

### CreateFromEmailButton

**Props**:

```typescript
interface CreateFromEmailButtonProps {
  threadId: string;              // Required
  company?: string;              // Optional hint
  role?: string;                 // Optional hint
  sender?: string;               // Email sender
  subject?: string;              // Email subject
  bodyText?: string;             // Email body
  headers?: Record<string, string>; // Email headers
  source?: string;               // Optional hint
  onPrefill?: (prefill) => void; // Callback for prefill
  onCreated?: () => void;        // Callback after save
}
```text

**Usage in Tracker**:

```typescript
{r.thread_id && (
  <CreateFromEmailButton
    threadId={r.thread_id}
    company={r.company}
    role={r.role}
    source={r.source || undefined}
    onPrefill={(prefill) => openCreateWithPrefill(prefill)}
    onCreated={() => fetchRows()}
  />
)}
```text

**Buttons**:

- **"Create from Email"** → Calls backfill, saves immediately
- **"Prefill Only"** → Calls extract, opens dialog with prefilled fields

### openCreateWithPrefill

**Function**:

```typescript
const openCreateWithPrefill = (prefill?: Partial<typeof form>) => {
  if (prefill) {
    setForm((f) => ({ ...f, ...prefill }))
  }
  ;(document.getElementById('create-dialog') as any)?.showModal?.()
}
```text

**Purpose**: Merge extracted fields into form and open create dialog

## 🔍 Extraction Heuristics

### Company Detection

1. Extract domain from sender email (skip gmail/outlook/yahoo)
2. Scan signature blocks (first 30 lines)
3. Look for "Jane from Acme" patterns
4. Parse display name

### Role Extraction

- **Primary**: Subject line matching (engineer|designer|manager|scientist|analyst|developer|lead)
- **Fallback**: Body text matching
- **Pattern**: `/(for|—|-)\s*(...role keywords...)/i`

### Source Detection

- **Headers**: `List-Unsubscribe`, `X-Mailer`, `Received`
- **Known ATS**: Greenhouse, Lever, Workday (domain/header matching)
- **Body Keywords**: Recruiting platform signatures

## 🧪 Testing

### Manual Test Flow

1. Start dev environment
2. Navigate to <http://localhost:5175/tracker>
3. Find a row with `thread_id` (shows button)
4. Click **"Prefill Only"**:
   - ✅ Dialog opens
   - ✅ Fields are prefilled
   - ✅ Toast shows extraction results
5. Click **"Create from Email"**:
   - ✅ Application created
   - ✅ Success toast appears
   - ✅ List refreshes

### cURL Testing

```bash
# Test extraction
curl -X POST http://localhost:8003/api/applications/extract \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Re: Application for ML Engineer",
    "from": "recruiter@acme.ai",
    "text": "Thanks for your application to Acme Corp..."
  }'

# Test backfill
curl -X POST http://localhost:8003/api/applications/backfill-from-email \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "test123",
    "subject": "Re: Application for ML Engineer",
    "from": "recruiter@acme.ai",
    "text": "Thanks for your application..."
  }'
```text

### Check Database

```bash
# Connect to SQLite/PostgreSQL
sqlite3 path/to/applylens.db

# Query applications
SELECT id, company, role, source, source_confidence, thread_id 
FROM applications 
ORDER BY created_at DESC 
LIMIT 10;

# Check for duplicates
SELECT thread_id, COUNT(*) 
FROM applications 
WHERE thread_id IS NOT NULL 
GROUP BY thread_id 
HAVING COUNT(*) > 1;
```text

## 🐛 Debugging

### Backend Logs

```bash
# Start with debug logging
cd services/api
uvicorn app.main:app --reload --port 8003 --log-level debug
```text

### Frontend Console

Open browser DevTools (F12):

- Check Network tab for API calls
- Check Console for toast logs
- Look for `[Toast]` prefix in logs

### Common Issues

**Button Not Showing**:

- ✅ Check if row has `thread_id`
- ✅ Verify import in `Tracker.tsx`

**Extraction Returns Empty**:

- ✅ Check email content in request
- ✅ Verify `email_parsing.py` functions exist
- ✅ Test with sample data directly

**Duplicate Applications**:

- ✅ Check `thread_id` matching logic
- ✅ Verify company+role normalization
- ✅ Review confidence comparison

**Toast Not Appearing**:

- ✅ Check `useToast` hook
- ✅ Verify console logs
- ✅ Replace with global toast context

## 📁 File Locations

### Backend

- **Routes**: `services/api/app/routes_applications.py`
- **Models**: `services/api/app/models.py`
- **Parsing**: `services/api/app/email_parsing.py`
- **Tests**: `services/api/tests/test_email_parsing.py`

### Frontend

- **Button**: `apps/web/src/components/CreateFromEmailButton.tsx`
- **Tracker**: `apps/web/src/pages/Tracker.tsx`
- **Toast**: `apps/web/src/components/toast/useToast.ts`
- **Config**: `apps/web/vite.config.ts`

## 🔧 Configuration

### Backend Port

```python
# services/api/app/settings.py
API_PORT: int = 8003
```text

### Frontend Proxy

```typescript
// apps/web/vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8003',
      changeOrigin: true
    }
  }
}
```text

## 💡 Tips

### Improve Extraction Accuracy

1. Add more company patterns to `email_parsing.py`
2. Update role regex for domain-specific titles
3. Add more known ATS systems
4. Increase confidence thresholds

### Performance Optimization

1. Cache extraction results by thread_id
2. Batch process multiple emails
3. Add database indexes on `thread_id`, `company`, `role`

### User Experience

1. Show extraction confidence in UI
2. Allow manual override of extracted fields
3. Add extraction preview before saving
4. Show diff when updating existing application

## 🎯 Quick Commands

```bash
# Start everything
cd services/api && uvicorn app.main:app --reload --port 8003 &
cd apps/web && npm run dev

# Test extraction
curl -X POST localhost:8003/api/applications/extract \
  -H "Content-Type: application/json" \
  -d '{"subject":"Engineer role","from":"jane@acme.ai","text":"Apply now"}'

# Check database
sqlite3 applylens.db "SELECT * FROM applications ORDER BY id DESC LIMIT 5"

# Run tests
cd services/api && pytest tests/test_email_parsing.py
cd apps/web && npm run test:e2e
```text

## 📚 Related Docs

- **Full Implementation**: `EMAIL_EXTRACTION_FEATURE_COMPLETE.md`
- **Heuristics Details**: `EMAIL_PARSING_HEURISTICS_APPLIED.md`
- **Tracker Guide**: `APPLICATION_TRACKER_QUICKSTART.md`
- **Development Setup**: `DEVELOPMENT.md`

---

**Need Help?** Check FastAPI docs at <http://localhost:8003/docs>
