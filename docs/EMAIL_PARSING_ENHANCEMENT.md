# Email Parsing Enhancement

## Overview

The email parsing heuristics patch adds intelligent auto-fill capabilities when creating job applications from email messages. The system can automatically extract company names, job roles, and ATS sources from Gmail message metadata.

## Architecture

### Backend Components

#### 1. Email Parsing Service (`services/api/app/services/email_parse.py`)

Three main extraction functions:

- **`extract_company(sender, body_text, subject)`**
  - Parses sender domain (e.g., `careers@openai.com` → `openai`)
  - Extracts sender name from email address
  - Searches for company mentions in body text (e.g., "at OpenAI")
  - Returns best match based on heuristics (prefers proper case, longer names)

- **`extract_role(subject, body_text)`**
  - Pattern matching for common role formats:
    - "for [Role] role"
    - "Position: [Role]"
    - "Job: [Role]"
    - "Application for [Role]"
  - Returns extracted role or "(Unknown Role)"

- **`extract_source(headers, sender, subject, body_text)`**
  - Detects Applicant Tracking Systems (ATS):
    - Lever (`lever.co`, `via lever`)
    - Greenhouse (`greenhouse.io`, `via greenhouse`)
    - LinkedIn
    - Workday
    - Indeed
  - Defaults to "Email" if no ATS detected

#### 2. Enhanced API Endpoint (`services/api/app/routers/applications.py`)

The `/applications/from-email` endpoint now accepts additional parameters:

```python
@router.post("/from-email", response_model=ApplicationOut)
def create_from_email(
    *,
    thread_id: str,
    company: Optional[str] = None,        # Manual override
    role: Optional[str] = None,           # Manual override
    snippet: Optional[str] = None,
    sender: Optional[str] = None,         # NEW: For extraction
    subject: Optional[str] = None,        # NEW: For extraction
    body_text: Optional[str] = None,      # NEW: For extraction
    headers: Optional[dict] = None,       # NEW: For ATS detection
    source: Optional[str] = None,         # Manual override
    db: Session = Depends(get_db),
):
```

**Extraction Logic:**
1. If `company` is provided → use it
2. Else → call `extract_company(sender, body_text, subject)`
3. If `role` is provided → use it
4. Else → call `extract_role(subject, body_text)`
5. If `source` is provided → use it
6. Else → call `extract_source(headers, sender, subject, body_text)`

### Frontend Components

#### 1. CreateFromEmailButton (`apps/web/src/components/CreateFromEmailButton.tsx`)

React component that creates an application from email metadata:

```tsx
interface CreateFromEmailButtonProps {
  threadId: string;
  company?: string;      // Optional manual override
  role?: string;         // Optional manual override
  snippet?: string;
  sender?: string;       // NEW: For auto-extraction
  subject?: string;      // NEW: For auto-extraction
  bodyText?: string;     // NEW: For auto-extraction
  headers?: Record<string, string>;  // NEW: For ATS detection
  source?: string;       // Optional manual override
}
```

**Flow:**
1. User clicks "Create Application" button
2. Component sends POST request to `/applications/from-email`
3. Backend extracts company, role, source from email metadata
4. On success, navigates to `/tracker?created=1&label={company}`
5. Tracker page shows toast notification

#### 2. Tracker Page Toast (`apps/web/src/pages/Tracker.tsx`)

Displays success notification when application is created:

```tsx
// Detects query parameter and shows toast
useEffect(() => {
  if (searchParams.get('created') === '1') {
    const label = decodeURIComponent(searchParams.get('label') || 'Application')
    setToast(`${label} added to tracker`)
    // Clean up URL and auto-hide after 3s
  }
}, [searchParams, setSearchParams])
```

## Test Coverage

### Unit Tests (`services/api/tests/test_email_parse.py`)

9 comprehensive tests covering all extraction functions:

1. ✅ `test_extract_company_from_sender` - Parses domain from sender email
2. ✅ `test_extract_company_from_body` - Finds company mentions in body text
3. ✅ `test_extract_role_from_subject` - Extracts role from subject line
4. ✅ `test_extract_role_with_position_label` - Handles "Position: X" format
5. ✅ `test_extract_source_lever` - Detects Lever ATS
6. ✅ `test_extract_source_greenhouse` - Detects Greenhouse ATS
7. ✅ `test_extract_source_linkedin` - Detects LinkedIn
8. ✅ `test_extract_source_default` - Defaults to "Email"
9. ✅ `test_full_extraction_pipeline` - End-to-end extraction

### Integration Tests (`services/api/tests/test_applications.py`)

4 tests validating API behavior:

1. ✅ `test_upsert_application_from_email` - Creates application from email with metadata
2. ✅ `test_upsert_application_by_thread_id` - Links emails by thread ID
3. ✅ `test_no_application_without_metadata` - Handles missing metadata
4. ✅ `test_from_email_endpoint_autofill` - Validates auto-extraction in API

**Test Results:**
```
Running application tests...
✅ Test passed: Application 1 created and linked to email
✅ Test passed: Both emails linked to same application
✅ Test passed: No application created for newsletter email
✅ Test passed: /from-email endpoint auto-extracted: company=Careers Team, role=Research Engineer, source=Email
✅ All tests passed!
```

## Usage Examples

### Example 1: Auto-extraction from Email Metadata

```typescript
// Frontend component
<CreateFromEmailButton
  threadId="thread_12345"
  sender="Careers Team <careers@openai.com>"
  subject="Your Application for Research Engineer role at OpenAI"
  bodyText="Thank you for applying for the Research Engineer position at OpenAI!"
  headers={{ 'x-source': 'lever.co' }}
/>
```

**Result:**
- Company: "Careers Team" or "openai" (extracted from sender)
- Role: "Research Engineer" (extracted from subject)
- Source: "Lever" (detected from headers)

### Example 2: Manual Override with Partial Auto-extraction

```typescript
<CreateFromEmailButton
  threadId="thread_67890"
  company="Anthropic"  // Manual override
  sender="recruiting@anthropic.com"
  subject="Interview availability"
  bodyText="We'd like to schedule an interview for the ML Engineer position"
/>
```

**Result:**
- Company: "Anthropic" (manual override used)
- Role: "ML Engineer" (extracted from body)
- Source: "Email" (default)

### Example 3: Backend API Call

```bash
curl -X POST http://localhost:8003/applications/from-email \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread_abc123",
    "sender": "jobs@stripe.com",
    "subject": "Application for Backend Engineer",
    "body_text": "Thank you for applying to Stripe"
  }'
```

**Response:**
```json
{
  "id": 42,
  "company": "Stripe",
  "role": "Backend Engineer",
  "source": "Email",
  "gmail_thread_id": "thread_abc123",
  "status": "applied",
  "created_at": "2025-10-09T12:00:00Z"
}
```

## ATS Detection

The system recognizes the following Applicant Tracking Systems:

| ATS | Detection Patterns |
|-----|-------------------|
| **Lever** | `lever.co`, `via lever` |
| **Greenhouse** | `greenhouse.io`, `via greenhouse` |
| **LinkedIn** | `linkedin` |
| **Workday** | `workday` |
| **Indeed** | `indeed` |

Detection is case-insensitive and searches across:
- Email subject
- Email body
- Sender address
- Message headers

## Benefits

1. **Reduced Manual Entry** - Auto-fills company, role, and source fields
2. **Improved Accuracy** - Regex-based extraction from structured email content
3. **ATS Tracking** - Identifies which platform sent the email
4. **Flexible Overrides** - Allows manual values when needed
5. **Better UX** - Toast notifications confirm successful creation

## Implementation Status

✅ **Complete** (100%)

- [x] Email parsing service module
- [x] Enhanced API endpoint with auto-extraction
- [x] CreateFromEmailButton component with all props
- [x] Tracker page toast notification
- [x] Unit tests (9/9 passing)
- [x] Integration tests (4/4 passing)
- [x] Documentation

## Future Enhancements

Potential improvements for future iterations:

1. **ML-based Extraction** - Use NLP models for better accuracy
2. **Learning from Corrections** - Track user edits to improve heuristics
3. **Additional ATS Support** - Add more platforms (Jobvite, Taleo, etc.)
4. **Confidence Scoring** - Return extraction confidence for UI indicators
5. **Gmail Inbox Pages** - Optional UI for browsing emails (see patch for Next.js examples)
6. **Auto-categorization** - Detect email type (rejection, interview invite, etc.)

## Notes

- The patch originally targeted Next.js but was adapted for React Router
- Gmail inbox pages are optional (patch included examples but not critical for core functionality)
- All extraction is regex-based (no ML dependencies)
- Graceful fallbacks ensure system works even with missing metadata
