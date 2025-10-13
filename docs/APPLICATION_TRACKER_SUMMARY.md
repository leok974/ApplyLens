# Application Tracker Implementation Summary

## Overview

Successfully implemented a complete application tracking system with automatic email linking, metadata extraction, and full CRUD API.

## Changes Made

### 1. Database Schema Updates (`app/models.py`)

- **Extended Email model** with:
  - `company` (VARCHAR 256, indexed) - extracted from sender/body
  - `role` (VARCHAR 512, indexed) - extracted from subject
  - `source` (VARCHAR 128, indexed) - ATS/source detection
  - `source_confidence` (FLOAT) - confidence score for source
  - `application_id` (INTEGER FK) - links to Application
  - Changed `from_addr/to_addr` to `sender/recipient`
  - Removed legacy `label` field (replaced by `label_heuristics` array)

- **Created Application model** with:
  - `id` (PRIMARY KEY)
  - `company` (VARCHAR 256, required, indexed)
  - `role` (VARCHAR 512, indexed)
  - `source` (VARCHAR 128, indexed)
  - `source_confidence` (FLOAT)
  - `thread_id` (VARCHAR 128, indexed) - Gmail thread grouping
  - `last_email_id` (INTEGER FK to emails)
  - `status` (ENUM: applied, in_review, interview, offer, rejected, archived)
  - `notes` (TEXT)
  - `created_at`, `updated_at` (TIMESTAMP)

- **Added AppStatus enum**: applied, in_review, interview, offer, rejected, archived

### 2. Migration System (`app/migrate.py`)

- Created migration script with ALTER TABLE statements
- Adds columns to existing emails table
- Creates applications table with proper foreign keys
- Creates all necessary indexes
- Idempotent - can be run multiple times safely

### 3. Gmail Service Enhancements (`app/gmail_service.py`)

- **New extraction functions**:
  - `extract_company(sender, body)` - extracts company from sender domain or body text
  - `extract_role(subject)` - extracts job role from subject line
  - `extract_source(headers, sender, subject, body)` - detects ATS (Lever, Greenhouse, etc.)
  - `estimate_source_confidence(src)` - returns 0.0-0.9 confidence score

- **Application linking**:
  - `upsert_application_for_email(db, email)` - finds or creates Application
  - Groups emails by thread_id or company+role
  - Automatically updates application status based on email labels
  - Links email to application via foreign key

- **Updated gmail_backfill()**:
  - Calls extraction functions for each email
  - Saves company/role/source/confidence to Email
  - Calls upsert_application_for_email() after email saved
  - Indexes new fields in Elasticsearch

- **Updated ES mapping**:
  - Added `company` (keyword) for exact filtering
  - Added `role` (text with ats_analyzer) for searchability
  - Added `source` (keyword) for ATS filtering
  - Added `source_confidence` (float) for ranking

### 4. Applications CRUD API (`app/routes_applications.py`)

New router with full CRUD operations:

- **POST /applications** - Create new application
  - Body: company (required), role, source, status, notes, thread_id
  - Returns: AppOut with id, timestamps

- **GET /applications** - List applications
  - Query params: status, company, limit (default 500)
  - Filters by status enum or company name (ILIKE search)
  - Sorted by updated_at DESC

- **GET /applications/{app_id}** - Get single application
  - Returns full application details
  - 404 if not found

- **PATCH /applications/{app_id}** - Update application
  - Partial updates supported
  - Returns updated application

- **DELETE /applications/{app_id}** - Delete application
  - Returns {"ok": true}

- **POST /applications/from-email/{email_id}** - Create from email
  - Calls upsert_application_for_email()
  - Returns application_id and linked_email_id
  - 400 if email lacks company/role/thread

### 5. Enhanced Search (`app/routers/search.py`)

- Added `company` query parameter - filter by exact company name
- Added `source` query parameter - filter by ATS source
- Returns company, role, source in search results
- Multiple filters combine with AND logic

### 6. Testing (`tests/test_applications.py`)

Three comprehensive tests:

- **test_upsert_application_from_email()** - Creates app from email with metadata
- **test_upsert_application_by_thread_id()** - Verifies thread_id grouping
- **test_no_application_without_metadata()** - Ensures no app for newsletters

All tests pass successfully ✅

## API Endpoints Summary

### Applications CRUD

```
POST   /applications                    - Create application
GET    /applications                    - List applications (filters: status, company)
GET    /applications/{id}               - Get single application
PATCH  /applications/{id}               - Update application
DELETE /applications/{id}               - Delete application
POST   /applications/from-email/{id}   - Create from email
```

### Search Enhancements

```
GET    /search?q=...&company=...&source=...  - Search with filters
```

## Database Migration Commands

```bash
# Run migration (adds columns, creates tables)
docker compose exec api python -m app.migrate

# Verify schema
docker compose exec db psql -U postgres -d applylens -c "\d emails"
docker compose exec db psql -U postgres -d applylens -c "\d applications"
```

## Testing Commands

```bash
# Run all application tests
docker compose exec api python -m tests.test_applications

# Test endpoints
curl http://localhost:8003/applications
curl http://localhost:8003/docs#/applications
```

## Data Flow

### Email Backfill → Application Creation

1. User triggers backfill: `POST /gmail/backfill`
2. For each Gmail message:
   - Extract metadata: company, role, source, confidence
   - Save Email with extracted fields
   - Call `upsert_application_for_email()`
   - Find existing app by thread_id or company+role
   - If not found, create new Application
   - Set status based on label_heuristics
   - Link email.application_id → app.id
   - Index in Elasticsearch with new fields

### Manual Application Creation

1. User creates via API: `POST /applications`
2. Or from email: `POST /applications/from-email/{email_id}`
3. Application tracks all linked emails via relationship
4. User updates status: `PATCH /applications/{id}`

## Key Features

### Automatic Metadata Extraction

- **Company**: Extracted from sender domain or body patterns
- **Role**: Extracted from subject line patterns
- **Source**: Detects ATS (Lever, Greenhouse, Workday, etc.)
- **Confidence**: 0.9 for known ATS, 0.6 for headers, 0.4 for generic

### Intelligent Grouping

- Emails grouped by `thread_id` (Gmail conversation)
- Fallback to `company + role` matching
- Prevents duplicate applications for same job

### Status Tracking

- Enum ensures valid states
- Auto-sets to "interview" if label_heuristics contains "interview"
- Can be manually updated via PATCH endpoint

### Search Enhancement

- Filter search by company name
- Filter search by ATS source
- Combined with existing label filters
- Results include extracted metadata

## Frontend Integration Points

### Inbox UI Enhancements

Add to `EmailCard` component:

```typescript
// Show application link if email is linked
{email.application_id && (
  <Link to={`/tracker?app=${email.application_id}`}>
    📋 View Application
  </Link>
)}

// Add "Create Application" button
<button onClick={() => createFromEmail(email.id)}>
  ➕ Create Application
</button>
```

### Create Application from Email

```typescript
const createFromEmail = async (emailId: number) => {
  const res = await fetch(`/applications/from-email/${emailId}`, {
    method: 'POST'
  });
  const data = await res.json();
  navigate(`/tracker?selected=${data.application_id}`);
};
```

### Applications Tracker Page

New page at `/tracker` with:

- DataGrid showing all applications
- Filters: status dropdown, company search
- Columns: company, role, source, status, last updated
- Click row → view linked emails
- Status updates via dropdown
- Notes editor

## Performance Considerations

### Indexes Created

- `emails.gmail_id` (UNIQUE) - for upsert
- `emails.sender` - for company extraction
- `emails.company` - for application matching
- `emails.application_id` - for joins
- `applications.thread_id` - for email grouping
- `applications.company` - for search
- Composite: `(subject, sender, recipient)` - for full-text search

### Query Optimization

- Application list uses LIMIT 500
- Sorted by `updated_at DESC NULLS LAST`
- Uses indexes for status and company filters
- Elasticsearch filters reduce result set before scoring

## Security Considerations

- No authentication yet - add user_id FK to applications
- SQL injection prevented by SQLAlchemy ORM
- Input validation via Pydantic models
- Foreign key constraints ensure referential integrity

## Next Steps

### Immediate (Recommended)

1. **Frontend UI**: Create `/tracker` page with DataGrid
2. **Email linking UI**: Add "Create Application" button to EmailCard
3. **Elasticsearch reindex**: Delete index, run backfill to populate with new fields

### Future Enhancements

1. **ML Classification**: Replace regex with trained model
2. **Email Threading**: Show conversation view
3. **Analytics Dashboard**: Charts for status, source breakdown
4. **Scheduled Sync**: Cron job for automatic backfill
5. **Multi-user**: Add user_id to applications, OAuth per user
6. **Export**: CSV/PDF export of applications
7. **Reminders**: Notifications for follow-ups
8. **Attachments**: Store resume PDFs from emails

## Files Modified

### Backend

- `services/api/app/models.py` - Extended Email, created Application
- `services/api/app/migrate.py` - Migration script with ALTER TABLE
- `services/api/app/gmail_service.py` - Extraction functions, ES mapping
- `services/api/app/routes_applications.py` - NEW CRUD router
- `services/api/app/main.py` - Registered applications router
- `services/api/app/routers/search.py` - Added company/source filters
- `services/api/tests/test_applications.py` - NEW test suite

### Database

- `emails` table: +11 columns (gmail_id, sender, recipient, labels, label_heuristics, raw, company, role, source, source_confidence, application_id)
- `applications` table: NEW with 11 columns
- +13 indexes created

## Success Metrics

✅ All 7 implementation tasks completed
✅ Database migration successful
✅ API endpoints working (tested with curl)
✅ All 3 tests passing
✅ Foreign key relationships established
✅ Elasticsearch mapping updated
✅ API docs accessible at /docs

## Validation Commands

```bash
# Check API health
curl http://localhost:8003/health

# List applications (empty initially)
curl http://localhost:8003/applications

# Check API docs
open http://localhost:8003/docs#/applications

# Verify database schema
docker compose exec db psql -U postgres -d applylens -c "\d applications"

# Run tests
docker compose exec api python -m tests.test_applications
```

## Documentation

- API automatically documented at `/docs` with Swagger UI
- All endpoints have descriptions and schemas
- AppStatus enum values documented
- Query parameters documented with examples
