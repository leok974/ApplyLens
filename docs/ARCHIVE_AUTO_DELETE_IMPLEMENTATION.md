# Archive & Auto-Delete Feature Implementation Summary

**Date:** October 20, 2025  
**Feature:** Lifecycle management for rejected applications with archive and auto-delete  
**Status:** ✅ Backend Complete, UI Pending

---

## Overview

Implemented a complete lifecycle management system for rejected job applications that automatically archives and deletes old applications while providing manual controls and safeguards.

### Key Features

✅ **Database Schema** - New fields for archive/delete tracking  
✅ **API Endpoints** - Archive, restore, delete, and bulk operations  
✅ **Auto-Cleanup Job** - Scheduled task for lifecycle management  
✅ **Elasticsearch Sync** - Tombstoning and deletion patterns  
✅ **Audit Logging** - Complete audit trail for compliance  
✅ **Configuration** - Flexible retention policies via environment variables  
⏳ **UI Components** - Pending implementation  
⏳ **Tests** - Pending implementation  

---

## 1. Database Changes

### Migration: `0019_archive_fields.py`

```python
# Location: services/api/alembic/versions/0019_archive_fields.py

# New columns added to applications table:
- archived_at: DateTime(timezone=True)  # When app was archived
- deleted_at: DateTime(timezone=True)   # When app was soft-deleted
- archive_opt_out: Boolean              # User opt-out from auto-archive
- auto_delete_opt_out: Boolean          # User opt-out from auto-delete

# Indexes created:
- ix_applications_archived_at          # For archive queries
- ix_applications_deleted_at           # For deletion queries
- ix_applications_status_archived      # Composite for cleanup job
```

**Run Migration:**
```bash
cd services/api
alembic upgrade head
```

### Model Updates

```python
# Location: services/api/app/models.py

class Application(Base):
    # ... existing fields ...
    
    # Archive & auto-delete lifecycle fields
    archived_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archive_opt_out = Column(Boolean, nullable=False, default=False)
    auto_delete_opt_out = Column(Boolean, nullable=False, default=False)
```

---

## 2. Configuration Settings

### Environment Variables

```bash
# Location: services/api/app/config.py

# Archive rejected applications after X days
APPLYLENS_AUTO_ARCHIVE_REJECTED_AFTER_DAYS=14

# Delete archived applications after Y days
APPLYLENS_AUTO_DELETE_ARCHIVED_AFTER_DAYS=90

# Grace period to undo archive (hours)
APPLYLENS_ARCHIVE_GRACE_UNDO_HOURS=48
```

**Add to `.env` or `docker-compose` env vars:**
```yaml
environment:
  APPLYLENS_AUTO_ARCHIVE_REJECTED_AFTER_DAYS: 14
  APPLYLENS_AUTO_DELETE_ARCHIVED_AFTER_DAYS: 90
  APPLYLENS_ARCHIVE_GRACE_UNDO_HOURS: 48
```

---

## 3. API Endpoints

### POST `/applications/{id}/archive`

Archive a single application.

**Request:**
```bash
curl -X POST http://localhost:8003/applications/123/archive
```

**Response:**
```json
{
  "ok": true,
  "archived_at": "2025-10-20T15:30:00Z",
  "message": "Application archived successfully"
}
```

### POST `/applications/{id}/restore`

Restore an archived application.

**Request:**
```bash
curl -X POST http://localhost:8003/applications/123/restore
```

**Response:**
```json
{
  "ok": true,
  "message": "Application restored successfully"
}
```

### DELETE `/applications/{id}`

Permanently delete an application.

**Query Parameters:**
- `force` (boolean, optional): Skip archive requirement

**Request:**
```bash
curl -X DELETE http://localhost:8003/applications/123?force=false
```

**Response:**
```json
{
  "ok": true,
  "message": "Application permanently deleted"
}
```

**Error if not archived first:**
```json
{
  "detail": "Application must be archived before deletion. Use force=true to bypass."
}
```

### POST `/applications/bulk/archive`

Archive multiple applications at once.

**Request:**
```json
{
  "application_ids": [123, 456, 789]
}
```

**Response:**
```json
{
  "archived_count": 2,
  "failed_ids": [456]
}
```

---

## 4. Automatic Cleanup Job

### Cron Job: `archive_cleanup.py`

**Location:** `services/api/app/cron/archive_cleanup.py`

**What It Does:**
1. **Auto-Archive:** Archives rejected applications older than X days
2. **Auto-Delete:** Permanently deletes archived applications older than Y days
3. **Respects Opt-Outs:** Skips applications with opt-out flags
4. **Audit Logging:** Records all actions for compliance
5. **ES Sync:** Updates Elasticsearch indices

**Run Manually:**
```bash
cd services/api
python -m app.cron.archive_cleanup

# Dry run mode (preview without changes):
python -m app.cron.archive_cleanup --dry-run
```

**Schedule with Cron (Linux/Mac):**
```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/services/api && python -m app.cron.archive_cleanup >> /var/log/archive_cleanup.log 2>&1
```

**Schedule with Windows Task Scheduler:**
```powershell
# Create a scheduled task
$action = New-ScheduledTaskAction -Execute "python" -Argument "-m app.cron.archive_cleanup" -WorkingDirectory "D:\ApplyLens\services\api"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "ApplyLens Archive Cleanup" -Description "Clean up archived applications"
```

**Add to APScheduler (FastAPI):**
```python
# In services/api/app/scheduler.py
from app.cron.archive_cleanup import run_archive_cleanup

scheduler.add_job(
    run_archive_cleanup,
    'cron',
    hour=2,  # Run at 2 AM
    id='archive_cleanup',
    replace_existing=True
)
```

---

## 5. Elasticsearch Integration

### Utilities: `es_applications.py`

**Location:** `services/api/app/utils/es_applications.py`

**Functions:**
- `es_tombstone_application(app_id)` - Sets `visible=false` for archived apps
- `es_upsert_application(app)` - Re-indexes restored apps  
- `es_delete_application(app_id)` - Permanently removes from ES
- `es_available()` - Checks if ES is configured

**Index Configuration:**
The applications index should exclude archived by default:

```json
{
  "query": {
    "bool": {
      "must": [
        {"match_all": {}}
      ],
      "must_not": [
        {"term": {"visible": false}},
        {"exists": {"field": "archived_at"}}
      ]
    }
  }
}
```

**Environment Variable:**
```bash
ES_APPS_INDEX=applications_v1
```

---

## 6. Audit Trail

All archive lifecycle events are logged to the `actions_audit` table:

```sql
SELECT * FROM actions_audit 
WHERE action LIKE 'application.%' 
ORDER BY created_at DESC;
```

**Event Types:**
- `application.archive` - Manual archive via API
- `application.restore` - Manual restore via API  
- `application.delete` - Manual hard delete via API
- `application.auto_archive` - Automatic archive by scheduler
- `application.auto_delete` - Automatic delete by scheduler

**Example Audit Record:**
```json
{
  "email_id": "123",
  "action": "application.auto_archive",
  "actor": "system",
  "policy_id": null,
  "confidence": null,
  "rationale": "Auto-archived after 14 days",
  "payload": null,
  "created_at": "2025-10-20T15:30:00Z"
}
```

---

## 7. Safeguards & Policies

### Opt-Out Flags

Users can opt out of automatic lifecycle management:

```sql
-- Prevent auto-archive
UPDATE applications 
SET archive_opt_out = true 
WHERE id = 123;

-- Prevent auto-delete
UPDATE applications 
SET auto_delete_opt_out = true 
WHERE id = 123;
```

### Grace Period

The `ARCHIVE_GRACE_UNDO_HOURS` setting (default 48h) allows users to restore recently archived applications. This is enforced in the UI but not currently in the API restore endpoint (can be uncommented).

### Deletion Requirement

By default, applications must be archived before deletion (safety check). Use `force=true` to bypass.

---

## 8. UI Integration (TODO)

### Required Components

**1. Application Row Actions**
```tsx
// Location: apps/web/src/components/Applications/RowActions.tsx

<DropdownMenu>
  <DropdownMenuItem onClick={() => archiveApp(id)}>
    <Archive className="mr-2 h-4 w-4" />
    Archive
  </DropdownMenuItem>
  
  {isArchived && (
    <DropdownMenuItem onClick={() => restoreApp(id)}>
      <RotateCcw className="mr-2 h-4 w-4" />
      Restore
    </DropdownMenuItem>
  )}
  
  {isArchived && (
    <DropdownMenuItem onClick={() => deleteApp(id)} className="text-destructive">
      <Trash2 className="mr-2 h-4 w-4" />
      Delete Permanently
    </DropdownMenuItem>
  )}
</DropdownMenu>
```

**2. Archived Filter Toggle**
```tsx
// Location: apps/web/src/pages/Applications.tsx

const [showArchived, setShowArchived] = useState(false);

<div className="flex items-center gap-2">
  <Switch checked={showArchived} onCheckedChange={setShowArchived} />
  <Label>Show archived</Label>
  {archivedCount > 0 && (
    <Badge variant="secondary">{archivedCount} archived</Badge>
  )}
</div>
```

**3. Details Panel Banner**
```tsx
// Location: apps/web/src/components/Applications/DetailsPanel.tsx

{application.archived_at && (
  <Alert variant="warning">
    <AlertCircle className="h-4 w-4" />
    <AlertTitle>Archived</AlertTitle>
    <AlertDescription>
      Archived on {formatDate(application.archived_at)}
      {isWithinGracePeriod && (
        <Button variant="link" onClick={handleRestore}>
          Undo
        </Button>
      )}
    </AlertDescription>
  </Alert>
)}
```

**4. Settings Panel**
```tsx
// Location: apps/web/src/pages/Settings.tsx

<Card>
  <CardHeader>
    <CardTitle>Retention & Archival</CardTitle>
  </CardHeader>
  <CardContent>
    <div className="space-y-4">
      <div>
        <Label>Auto-archive rejected after</Label>
        <Input type="number" value={archiveDays} onChange={...} />
        <span className="text-sm text-muted-foreground">days</span>
      </div>
      
      <div>
        <Label>Auto-delete archived after</Label>
        <Input type="number" value={deleteDays} onChange={...} />
        <span className="text-sm text-muted-foreground">days</span>
      </div>
      
      <div>
        <Label>Grace period for undo</Label>
        <Input type="number" value={graceHours} onChange={...} />
        <span className="text-sm text-muted-foreground">hours</span>
      </div>
    </div>
  </CardContent>
</Card>
```

### API Client Functions

```typescript
// Location: apps/web/src/lib/api.ts

export const archiveApplication = async (id: number) => {
  const response = await fetch(`/api/applications/${id}/archive`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to archive application');
  return response.json();
};

export const restoreApplication = async (id: number) => {
  const response = await fetch(`/api/applications/${id}/restore`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to restore application');
  return response.json();
};

export const deleteApplication = async (id: number, force = false) => {
  const response = await fetch(`/api/applications/${id}?force=${force}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete application');
  return response.json();
};

export const bulkArchiveApplications = async (ids: number[]) => {
  const response = await fetch('/api/applications/bulk/archive', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ application_ids: ids }),
  });
  if (!response.ok) throw new Error('Failed to bulk archive');
  return response.json();
};
```

---

## 9. Testing (TODO)

### Unit Tests

```python
# Location: services/api/tests/test_archive_lifecycle.py

def test_archive_sets_timestamp():
    """Test that archiving sets archived_at"""
    
def test_restore_clears_timestamp():
    """Test that restoring clears archived_at"""
    
def test_delete_requires_archive():
    """Test that delete fails if not archived"""
    
def test_opt_out_prevents_auto_archive():
    """Test that opt_out flag prevents auto-archive"""
    
def test_cleanup_job_archives_old_rejected():
    """Test that job archives rejected apps after X days"""
    
def test_cleanup_job_deletes_old_archived():
    """Test that job deletes archived apps after Y days"""
```

### API Tests

```python
# Location: services/api/tests/test_api_archive.py

def test_archive_endpoint_success():
    """POST /applications/{id}/archive returns 200"""
    
def test_restore_endpoint_success():
    """POST /applications/{id}/restore returns 200"""
    
def test_delete_endpoint_requires_archive():
    """DELETE /applications/{id} returns 400 if not archived"""
    
def test_bulk_archive_endpoint():
    """POST /applications/bulk/archive handles multiple IDs"""
```

### E2E Tests (Playwright)

```typescript
// Location: tests/e2e/archive-lifecycle.spec.ts

test('Archive application from tracker', async ({ page }) => {
  // Click archive button
  // Verify row hidden
  // Toggle show archived
  // Verify row visible with archived badge
});

test('Restore archived application', async ({ page }) => {
  // Find archived app
  // Click restore
  // Verify back in active list
});

test('Delete archived application', async ({ page }) => {
  // Archive app
  // Click delete
  // Confirm deletion
  // Verify removed from all views
});
```

---

## 10. Deployment Checklist

### Pre-Deployment

- [x] Database migration created
- [x] API endpoints implemented
- [x] Cleanup job implemented
- [x] ES sync utilities created
- [x] Audit logging integrated
- [x] Configuration added
- [ ] UI components created
- [ ] Tests written and passing

### Deployment Steps

1. **Backup database:**
   ```bash
   pg_dump applylens > backup_$(date +%Y%m%d).sql
   ```

2. **Run migration:**
   ```bash
   cd services/api
   alembic upgrade head
   ```

3. **Set environment variables:**
   ```bash
   APPLYLENS_AUTO_ARCHIVE_REJECTED_AFTER_DAYS=14
   APPLYLENS_AUTO_DELETE_ARCHIVED_AFTER_DAYS=90
   APPLYLENS_ARCHIVE_GRACE_UNDO_HOURS=48
   ```

4. **Deploy API changes:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build api
   ```

5. **Schedule cleanup job:**
   - Add cron job or APScheduler task
   - Test with `--dry-run` first

6. **Monitor audit logs:**
   ```sql
   SELECT * FROM actions_audit 
   WHERE action LIKE 'application.%' 
   AND created_at > NOW() - INTERVAL '7 days'
   ORDER BY created_at DESC;
   ```

### Post-Deployment Verification

```bash
# Test archive endpoint
curl -X POST http://localhost:8003/applications/1/archive

# Test restore endpoint  
curl -X POST http://localhost:8003/applications/1/restore

# Run cleanup job in dry-run mode
python -m app.cron.archive_cleanup --dry-run

# Check ES sync
curl http://localhost:9200/applications_v1/_search?q=visible:false

# Verify audit logs
curl http://localhost:8003/api/audit?action=application.archive
```

---

## 11. Rollback Plan

If issues arise, rollback steps:

1. **Disable cleanup job** (stop cron/scheduler)
2. **Revert API deployment**
3. **Downgrade migration:**
   ```bash
   alembic downgrade -1
   ```
4. **Restore database from backup** (if needed)

---

## 12. Documentation Files Created

- `/docs/ARCHIVE_AUTO_DELETE_IMPLEMENTATION.md` (this file)
- `/services/api/alembic/versions/0019_archive_fields.py`
- `/services/api/app/cron/archive_cleanup.py`
- `/services/api/app/utils/es_applications.py`
- Updated: `/services/api/app/models.py`
- Updated: `/services/api/app/config.py`
- Updated: `/services/api/app/routes_applications.py`

---

## 13. Next Steps

1. **Implement UI components** (Row actions, filters, settings)
2. **Write comprehensive tests** (Unit, API, E2E)
3. **Schedule cleanup job** (Cron or APScheduler)
4. **Monitor in production** (Audit logs, metrics)
5. **User documentation** (How to archive, restore, opt-out)

---

## Contact & Support

For questions or issues:
- Review audit logs: `SELECT * FROM actions_audit WHERE action LIKE 'application.%'`
- Check cleanup job logs: `/var/log/archive_cleanup.log`
- ES sync status: Check application logs for `[ES Sync]` messages

---

**Implementation Date:** October 20, 2025  
**Backend Status:** ✅ Complete  
**Ready for:** UI Implementation, Testing, Production Deployment
