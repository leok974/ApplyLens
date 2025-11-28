# Tracker-Mail Integration

## Overview

The Tracker page now provides bidirectional linking between job applications and email threads, creating a seamless loop between the Mail/Inbox view and Application Tracker.

**Feature Status**: ✅ Production Ready (v0.5.15+)

---

## User Experience

### From Mail → Tracker

1. User views an email thread in MailChat
2. Clicks "Create Application" to backfill job application data
3. Application created with `thread_id` link preserved
4. User navigates to Tracker page
5. **Sees "Mail" badge** next to application
6. Clicks badge → Opens original Gmail thread in new tab

### Benefits

- **Context Preservation**: Never lose track of which email led to an application
- **Quick Navigation**: One-click access from Tracker back to original conversation
- **Status Tracking**: See application status alongside email context

---

## Implementation Details

### 1. Frontend UI (TrackerPage)

**File**: `apps/web/src/pages/TrackerPage.tsx`

**Component**: `MailBadge`
```tsx
{app.thread_id && (
  <button
    onClick={(e) => {
      e.stopPropagation();
      window.open(
        `https://mail.google.com/mail/u/0/#all/${app.thread_id}`,
        '_blank',
        'noopener,noreferrer'
      );
    }}
    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-yellow-50 text-yellow-700 hover:bg-yellow-100 dark:bg-yellow-900/20 dark:text-yellow-400 dark:hover:bg-yellow-900/30 transition-colors"
    title="View original email thread"
  >
    <Mail className="h-3 w-3" />
    Mail
  </button>
)}
```

**Styling**:
- Uses yellow accent (matches ThreadList/ThreadViewer)
- Dark mode compatible
- Hover effects for interactivity
- Icon + text for clarity

**Position**: Displayed inline with company name and source badge

### 2. Backend Data Flow

**Endpoint**: `POST /api/applications/backfill-from-email`

**Request**:
```json
{
  "thread_id": "19339e8a12345678",
  "company": "Example Corp",
  "position": "Software Engineer",
  "status": "applied",
  "source": "email"
}
```

**Response**:
```json
{
  "id": "app_123",
  "thread_id": "19339e8a12345678",
  "company": "Example Corp",
  "position": "Software Engineer",
  "status": "applied",
  "source": "email",
  "created_at": "2025-11-20T12:00:00Z"
}
```

**Database Schema**:
```sql
CREATE TABLE applications (
  id VARCHAR PRIMARY KEY,
  thread_id VARCHAR,  -- Gmail thread ID (nullable)
  company VARCHAR,
  position VARCHAR,
  status VARCHAR,
  source VARCHAR,
  created_at TIMESTAMP
);

CREATE INDEX idx_applications_thread_id ON applications(thread_id);
```

### 3. Metrics & Telemetry

**Metric**: `applylens_applications_created_from_thread_total`

**Type**: Counter (Prometheus)

**Labels**:
- `source`: Always "email" for thread-based applications
- `status`: Application status (applied/interview/offer/rejected)

**Increment Location**: `services/api/app/routers/applications.py`

```python
from app.metrics import applications_created_from_thread_total

@router.post("/backfill-from-email")
async def backfill_from_email(req: BackfillRequest):
    # Create application...

    # Increment metric
    applications_created_from_thread_total.labels(
        source=application.source,
        status=application.status
    ).inc()

    return application
```

**Grafana Query**:
```promql
# Total applications created from email threads
sum(applylens_applications_created_from_thread_total)

# Rate over time
rate(applylens_applications_created_from_thread_total[5m])

# By status
sum by (status) (applylens_applications_created_from_thread_total)
```

---

## Testing

### Unit Tests (Vitest)

**File**: `apps/web/src/pages/TrackerPage.test.tsx`

**Coverage**:
- ✅ Renders Mail badge when `thread_id` exists (6 tests)
- ✅ Opens Gmail in new tab on click
- ✅ No badge when `thread_id` is null
- ✅ Event propagation stopped
- ✅ Dark mode styling
- ✅ Accessibility (title attribute)

**Run Tests**:
```bash
cd apps/web
npm test TrackerPage
```

### Backend Tests

**File**: `services/api/tests/test_applications.py`

**Coverage**:
- ✅ Metric increments when creating from thread
- ✅ Correct labels applied (source, status)
- ✅ Thread ID preserved in database

**Run Tests**:
```bash
cd services/api
pytest tests/test_applications.py -v
```

### Manual Testing Checklist

- [ ] Create application from email thread in MailChat
- [ ] Navigate to Tracker page
- [ ] Verify Mail badge appears
- [ ] Click badge
- [ ] Confirm Gmail opens in new tab with correct thread
- [ ] Verify Prometheus metric increments in Grafana
- [ ] Test in light and dark mode
- [ ] Test with applications without thread_id (no badge should show)

---

## Production Deployment

### Prerequisites

- API version: `0.5.15+`
- Web version: `0.5.18+`
- Database migration: `20251120_add_thread_id_to_applications` (if not already applied)

### Deployment Steps

1. **Run migration** (if needed):
   ```bash
   docker exec applylens-api-prod alembic upgrade head
   ```

2. **Deploy backend**:
   ```bash
   docker-compose -f docker-compose.prod.yml pull api
   docker-compose -f docker-compose.prod.yml up -d api
   ```

3. **Deploy frontend**:
   ```bash
   docker-compose -f docker-compose.prod.yml pull web
   docker-compose -f docker-compose.prod.yml up -d web
   ```

4. **Verify deployment**:
   ```bash
   # Check API health
   curl https://applylens.app/api/healthz

   # Check Prometheus metrics endpoint
   curl http://localhost:8003/metrics | grep applylens_applications_created_from_thread
   ```

### Monitoring

**Grafana Dashboard**: "Application Tracker Overview"

**Panels**:
1. **Applications Created from Email** (graph)
   - Query: `rate(applylens_applications_created_from_thread_total[5m])`
   - Shows creation rate over time

2. **Total Email-Linked Applications** (stat)
   - Query: `sum(applylens_applications_created_from_thread_total)`
   - Shows total count since deployment

3. **Applications by Status** (pie chart)
   - Query: `sum by (status) (applylens_applications_created_from_thread_total)`
   - Breaks down applied/interview/offer/rejected

**Alerts**:
```yaml
# Example alert for low engagement
- alert: LowEmailToTrackerConversion
  expr: rate(applylens_applications_created_from_thread_total[1h]) < 0.01
  for: 6h
  labels:
    severity: info
  annotations:
    summary: "Few applications being created from email threads"
    description: "Only {{ $value }} applications/hour created from threads in last hour"
```

---

## Usage Analytics

### Key Metrics

1. **Adoption Rate**: % of applications with `thread_id`
   ```sql
   SELECT
     COUNT(*) FILTER (WHERE thread_id IS NOT NULL) * 100.0 / COUNT(*) as adoption_rate
   FROM applications;
   ```

2. **Badge Click Rate**: Track via frontend analytics
   ```typescript
   // In MailBadge onClick
   analytics.track('tracker_mail_badge_clicked', {
     application_id: app.id,
     thread_id: app.thread_id
   });
   ```

3. **Conversion Funnel**:
   - Threads viewed in MailChat
   - "Create Application" button clicks
   - Applications created with thread_id
   - Mail badges clicked on Tracker

---

## Future Enhancements

### Phase 2: Bidirectional Status Sync

**Goal**: Show application status in ThreadList

**Implementation**:
1. Query application status when loading threads
2. Display status pill in ThreadList (e.g., "Applied 3 days ago")
3. Update status from thread view

**Benefits**:
- See application progress without leaving email
- Contextual reminders to follow up
- Unified view of job search pipeline

### Phase 3: Smart Follow-ups

**Goal**: Suggest follow-up actions based on application status

**Examples**:
- "No response after 7 days → Send follow-up"
- "Interview scheduled → Prepare questions"
- "Offer received → Negotiate salary"

**Integration**:
- Agent V2 "followups" intent
- Tracker status as input
- Time-based triggers

---

## Troubleshooting

### Mail Badge Not Appearing

**Symptoms**: Application shows on Tracker but no Mail badge

**Causes**:
1. Application created before feature deployment
2. `thread_id` not saved during backfill
3. Frontend cache issue

**Fix**:
```sql
-- Check if thread_id exists
SELECT id, company, thread_id FROM applications WHERE id = 'app_123';

-- If null, backfill might have failed
-- Re-create application from MailChat
```

### Gmail Link Opens Wrong Thread

**Symptoms**: Badge opens but shows different/no thread

**Causes**:
1. Invalid thread_id format
2. Thread deleted from Gmail
3. User switched Gmail accounts

**Fix**:
- Verify thread_id format: `^[0-9a-f]{16}$`
- Check Gmail for thread existence
- Ensure user logged into correct account

### Metric Not Incrementing

**Symptoms**: Prometheus counter stays at 0

**Causes**:
1. Endpoint not being called
2. Metric label mismatch
3. Prometheus not scraping API

**Debug**:
```bash
# Check if metric exists
curl http://localhost:8003/metrics | grep applylens_applications

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="applylens-api")'

# Check application creation logs
docker logs applylens-api-prod | grep "backfill-from-email"
```

---

## Related Documentation

- [Tracker Page Implementation](./TRACKER.md)
- [MailChat Integration](./MAILCHAT.md)
- [Prometheus Metrics Guide](../infra/prometheus/README.md)
- [Application Backfill API](../services/api/docs/applications.md)

---

**Last Updated**: 2025-11-20
**Owners**: Engineering Team
**Status**: ✅ Production
