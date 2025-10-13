# Application Tracker - Quick Start Guide

## What's New?

The ApplyLens system now automatically tracks job applications by analyzing your emails! When you sync Gmail, the system:

1. **Extracts metadata** from each email:
   - Company name (from sender domain or email body)
   - Job role (from subject line)
   - ATS/source (Lever, Greenhouse, Workday, etc.)

2. **Groups related emails** by Gmail thread or company+role

3. **Creates Application records** that you can manage

4. **Tracks application status**: applied → in_review → interview → offer/rejected

## Using the API

### 1. Sync Gmail (automatically creates applications)

```bash
# Sync last 60 days of emails
POST http://localhost:8003/gmail/backfill
{
  "user_email": "you@example.com",
  "days": 60
}
```text

This will:

- Import all emails
- Extract company/role/source from each
- Create Application records grouped by thread
- Link emails to applications

### 2. List Your Applications

```bash
GET http://localhost:8003/applications
```text

Filter by status:

```bash
GET http://localhost:8003/applications?status=interview
```text

Filter by company:

```bash
GET http://localhost:8003/applications?company=Google
```text

### 3. Get Application Details

```bash
GET http://localhost:8003/applications/{id}
```text

Returns:

```json
{
  "id": 1,
  "company": "Google",
  "role": "Software Engineer",
  "source": "lever",
  "source_confidence": 0.9,
  "status": "interview",
  "thread_id": "abc123",
  "notes": "Had great conversation with recruiter",
  "created_at": "2025-10-01T12:00:00Z",
  "updated_at": "2025-10-08T15:30:00Z"
}
```text

### 4. Update Application Status

```bash
PATCH http://localhost:8003/applications/{id}
{
  "status": "offer",
  "notes": "Received offer, need to negotiate salary"
}
```text

Available statuses:

- `applied` - Initial application submitted
- `in_review` - Application under review
- `interview` - Interview scheduled/completed
- `offer` - Offer received
- `rejected` - Application rejected
- `archived` - Old/inactive application

### 5. Create Application from Email

If an email wasn't automatically linked, you can manually create an application:

```bash
POST http://localhost:8003/applications/from-email/{email_id}
```text

Returns:

```json
{
  "application_id": 5,
  "linked_email_id": 123
}
```text

### 6. Search with Filters

```bash
# Search for "software engineer" at Google
GET http://localhost:8003/search?q=software engineer&company=Google

# Search for interviews from Lever
GET http://localhost:8003/search?q=interview&source=lever&label_filter=interview
```text

### 7. Create Application Manually

```bash
POST http://localhost:8003/applications
{
  "company": "Acme Corp",
  "role": "Senior Developer",
  "source": "linkedin",
  "status": "applied",
  "notes": "Applied via LinkedIn, waiting for response"
}
```text

### 8. Delete Application

```bash
DELETE http://localhost:8003/applications/{id}
```text

## Data Extracted from Emails

### Company Detection

- Extracts from sender email domain (e.g., `jobs@google.com` → "Google")
- Parses body text patterns (e.g., "We at Acme Corp would like...")
- Excludes generic domains (gmail, yahoo, etc.)

### Role Detection

- Parses subject lines for patterns like:
  - "Interview for Software Engineer"
  - "Application for: Senior Developer"
  - "Position: Data Scientist"

### Source Detection (ATS)

Automatically detects these application tracking systems:

- **Lever** (confidence: 0.9)
- **Greenhouse** (confidence: 0.9)
- **Workday** (confidence: 0.9)
- **SmartRecruiters** (confidence: 0.9)
- Email headers like `list-unsubscribe` (confidence: 0.6)
- Generic patterns (confidence: 0.4)

### Status Auto-Detection

When creating applications from emails:

- Contains "interview" → status = `interview`
- Otherwise → status = `applied`
- You can manually update later

## Frontend Integration (TODO)

### Add to EmailCard Component

```tsx
// Show linked application
{email.application_id && (
  <div className="mt-2">
    <Link to={`/tracker?app=${email.application_id}`} 
          className="text-blue-600 hover:underline">
      📋 View Application
    </Link>
  </div>
)}

// Add "Create Application" button
{!email.application_id && email.company && (
  <button 
    onClick={() => createFromEmail(email.id)}
    className="mt-2 px-3 py-1 bg-green-500 text-white rounded">
    ➕ Create Application
  </button>
)}
```text

### Create Tracker Page (`/tracker`)

```tsx
import { useState, useEffect } from 'react';

function TrackerPage() {
  const [applications, setApplications] = useState([]);
  const [filter, setFilter] = useState({ status: '', company: '' });
  
  useEffect(() => {
    const params = new URLSearchParams();
    if (filter.status) params.append('status', filter.status);
    if (filter.company) params.append('company', filter.company);
    
    fetch(`/applications?${params}`)
      .then(r => r.json())
      .then(setApplications);
  }, [filter]);
  
  return (
    <div>
      <h1>Job Applications Tracker</h1>
      
      {/* Filters */}
      <div className="filters">
        <select onChange={e => setFilter({...filter, status: e.target.value})}>
          <option value="">All Statuses</option>
          <option value="applied">Applied</option>
          <option value="interview">Interview</option>
          <option value="offer">Offer</option>
          <option value="rejected">Rejected</option>
        </select>
        
        <input 
          type="text" 
          placeholder="Company name"
          onChange={e => setFilter({...filter, company: e.target.value})}
        />
      </div>
      
      {/* Applications Grid */}
      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Role</th>
            <th>Source</th>
            <th>Status</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {applications.map(app => (
            <tr key={app.id}>
              <td>{app.company}</td>
              <td>{app.role}</td>
              <td><span className="badge">{app.source}</span></td>
              <td>
                <select 
                  value={app.status}
                  onChange={e => updateStatus(app.id, e.target.value)}>
                  <option value="applied">Applied</option>
                  <option value="in_review">In Review</option>
                  <option value="interview">Interview</option>
                  <option value="offer">Offer</option>
                  <option value="rejected">Rejected</option>
                  <option value="archived">Archived</option>
                </select>
              </td>
              <td>{new Date(app.updated_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```text

## Example Workflow

### Day 1: Initial Setup

1. Connect Gmail: Click "Connect Gmail" button
2. Sync emails: Click "Sync 60 days"
3. Wait for sync: ~30 seconds for 100 emails
4. Check applications: Navigate to `/tracker` page
5. See auto-created applications grouped by job

### Day 2: Manage Applications

1. Open tracker page
2. See application for "Google - Software Engineer"
3. Update status to "interview"
4. Add notes: "Phone screen scheduled for Oct 15"
5. Filter by status: "interview" to see all interviews

### Day 3: Email Arrives

1. Receive interview confirmation email
2. System auto-links to existing application (by thread_id)
3. Click "View Application" button on email
4. Taken to tracker page with application selected

### Day 4: Manual Entry

1. Applied to job via company website (not email)
2. Manually create: POST /applications
3. Add company, role, status, notes
4. Track alongside email-based applications

## Database Schema

### emails table

```text
id, gmail_id, thread_id, subject, body_text, 
sender, recipient, received_at, labels, label_heuristics, raw,
company, role, source, source_confidence, application_id
```text

### applications table

```text
id, company, role, source, source_confidence, 
thread_id, last_email_id, status, notes, 
created_at, updated_at
```text

### Relationships

- `emails.application_id` → `applications.id` (many-to-one)
- `applications.last_email_id` → `emails.id` (one-to-one)
- `applications.emails` → list of all linked emails (one-to-many)

## API Endpoints Summary

```text
# Gmail Operations
POST   /gmail/auth                     - Start OAuth flow
POST   /gmail/backfill                 - Sync emails (auto-creates apps)
GET    /gmail/status                   - Check connection status
GET    /gmail/inbox                    - List emails

# Applications CRUD
GET    /applications                   - List all applications
GET    /applications?status=interview  - Filter by status
GET    /applications?company=Google    - Filter by company
GET    /applications/{id}              - Get single application
POST   /applications                   - Create application
PATCH  /applications/{id}              - Update application
DELETE /applications/{id}              - Delete application
POST   /applications/from-email/{id}   - Create from email

# Search
GET    /search?q=...                   - Full-text search
GET    /search?q=...&company=Google    - Filter by company
GET    /search?q=...&source=lever      - Filter by ATS source
GET    /search?q=...&label_filter=interview - Filter by label
```text

## Testing

### Run Tests

```bash
docker compose exec api python -m tests.test_applications
```text

### Manual Testing via API Docs

1. Open: <http://localhost:8003/docs#/applications>
2. Expand any endpoint
3. Click "Try it out"
4. Fill in parameters
5. Click "Execute"
6. See response

### Test Data

```bash
# Create test application
curl -X POST http://localhost:8003/applications \
  -H "Content-Type: application/json" \
  -d '{
    "company": "TestCorp",
    "role": "QA Engineer",
    "status": "applied"
  }'

# List applications
curl http://localhost:8003/applications

# Update status
curl -X PATCH http://localhost:8003/applications/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "interview"}'
```text

## Troubleshooting

### No applications created after backfill

- Check that emails have recognizable company/role patterns
- Look at email sender domain (should not be gmail/yahoo)
- Check subject lines contain role keywords
- Manually create: POST /applications/from-email/{email_id}

### Duplicate applications

- System groups by thread_id first, then company+role
- If emails are in different threads, may create separate apps
- Manually merge by deleting one and updating emails

### Wrong company detected

- Extraction uses heuristics (sender domain + body patterns)
- May misidentify generic email addresses
- Manually update: PATCH /applications/{id} with correct company

### Status not auto-updating

- Only set during creation based on label_heuristics
- Manually update via API: PATCH /applications/{id}
- Future: webhooks to auto-update on new emails

## Performance Notes

- Backfill 60 days ~= 100-200 emails = ~30 seconds
- Application list limited to 500 by default
- Indexes on company, status, thread_id for fast queries
- Elasticsearch used for full-text search

## Security Notes

⚠️ **Current limitation**: No user authentication

- All users see all applications
- Anyone can modify/delete
- **TODO**: Add user_id FK to applications table
- **TODO**: Filter queries by current user

## Next Steps

1. **Build Frontend UI** - Create `/tracker` page
2. **Add "Create Application" button** - On EmailCard component  
3. **Test with real data** - Run backfill with your Gmail
4. **Add user authentication** - Multi-user support
5. **ML classification** - Replace regex with trained model
6. **Analytics dashboard** - Charts and insights
