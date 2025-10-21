# Kibana Data View & Saved Search Setup

**Date:** October 20, 2025  
**Status:** ✅ Applied Successfully  
**Kibana Version:** 8.13.4

---

## Overview

Created Kibana data view (index pattern) and saved search for easy email exploration and analysis via Kibana Discover.

---

## Components Created

### 1. Data View: "ApplyLens Emails"
**File:** `infra/kibana/emails_index_pattern.ndjson`  
**ID:** `919a7f6d-4431-451f-b5a6-7f3943524bd4`  
**Pattern:** `gmail_emails-*`  
**Time Field:** `received_at`

**Purpose:** Enables Kibana to search and visualize emails across all `gmail_emails-*` indices.

### 2. Saved Search: "ApplyLens — Emails (Active)"
**File:** `infra/kibana/emails_saved_search.ndjson`  
**ID:** `applylens-emails-discover`  
**Default Filter:** `archived:false`  
**Sort:** `received_at desc` (newest first)

**Columns Displayed:**
- `received_at` - When email was received
- `from` - Sender email (normalized)
- `to` - Recipient email (normalized)
- `subject` - Email subject
- `labels_norm` - Gmail labels (normalized)
- `is_interview` - Interview email flag
- `is_offer` - Job offer flag

**Column Widths:**
- `received_at`: 160px
- `from`: 240px
- `to`: 240px
- `subject`: 420px (wider for full visibility)

---

## Import Scripts

### PowerShell Script
**File:** `scripts/kibana-import.ps1`

**Usage:**
```powershell
.\scripts\kibana-import.ps1 -KbnUrl "http://localhost:5601" -User "elastic" -Pass "elasticpass"
```

**Features:**
- Imports both data view and saved search
- Handles multipart form data encoding
- Provides success/failure feedback
- Works with Kibana base path `/kibana`

### Bash Script
**File:** `scripts/kibana-import.sh`

**Usage:**
```bash
export KBN_URL=http://localhost:5601
export KBN_AUTH=elastic:elasticpass
./scripts/kibana-import.sh
```

**Note:** Requires `jq` for JSON parsing.

---

## Import Results

### Data View Import
```json
{
  "successCount": 1,
  "success": true,
  "successResults": [
    {
      "type": "index-pattern",
      "id": "applylens-emails",
      "meta": {
        "title": "ApplyLens Emails",
        "icon": "indexPatternApp"
      },
      "destinationId": "919a7f6d-4431-451f-b5a6-7f3943524bd4"
    }
  ]
}
```
✅ **Status:** Imported successfully

### Saved Search Import
```json
{
  "successCount": 1,
  "success": true,
  "successResults": [
    {
      "type": "search",
      "id": "applylens-emails-discover",
      "meta": {
        "title": "ApplyLens — Emails (Active)",
        "icon": "discoverApp"
      }
    }
  ]
}
```
✅ **Status:** Imported successfully

---

## Usage in Kibana

### Accessing Discover

1. **Open Kibana:**
   - URL: http://localhost:5601/kibana
   - Credentials: `elastic` / `elasticpass`

2. **Navigate to Discover:**
   - Menu → Analytics → Discover

3. **Select Data View:**
   - Data view dropdown → "ApplyLens Emails"

4. **Load Saved Search:**
   - Saved searches → "ApplyLens — Emails (Active)"

### Example Queries

**Active emails only (default):**
```
archived:false
```

**Interview emails:**
```
is_interview:true
```

**Job offers:**
```
is_offer:true
```

**Important inbox emails:**
```
labels_norm : "important" and labels_norm : "inbox"
```

**Emails from specific sender:**
```
from : "recruiter@acme.com"
```

**Subject contains keyword:**
```
subject : *interview*
```

**Combination:**
```
(is_interview:true or is_offer:true) and archived:false
```

### Time Range Selection

**Recommended ranges:**
- Last 7 days - Recent activity
- Last 30 days - Monthly view
- Last 90 days - Quarterly analysis
- Last year - Annual overview

---

## KQL (Kibana Query Language) Quick Reference

### Field Searches
```
field : value          # Exact match
field : *partial*      # Wildcard
field > 100            # Greater than
field >= 100           # Greater than or equal
field < 100            # Less than
field <= 100           # Less than or equal
```

### Boolean Operators
```
query1 and query2      # Both must match
query1 or query2       # Either must match
not query              # Must not match
```

### Field Existence
```
field : *              # Field exists
not field : *          # Field doesn't exist
```

### Arrays
```
labels_norm : "inbox"  # Array contains value
```

---

## Customization

### Creating Additional Saved Searches

**Interview & Offer Emails:**
```ndjson
{
  "type": "search",
  "id": "applylens-emails-opportunities",
  "attributes": {
    "title": "ApplyLens — Opportunities",
    "description": "Interview invites and job offers",
    "columns": ["received_at", "from", "subject", "is_interview", "is_offer"],
    "sort": [["received_at", "desc"]],
    "kibanaSavedObjectMeta": {
      "searchSourceJSON": "{\"query\":{\"query\":\"(is_interview:true or is_offer:true) and archived:false\",\"language\":\"kuery\"}}"
    }
  }
}
```

**Archived Emails:**
```ndjson
{
  "attributes": {
    "title": "ApplyLens — Archived",
    "kibanaSavedObjectMeta": {
      "searchSourceJSON": "{\"query\":{\"query\":\"archived:true\",\"language\":\"kuery\"}}"
    }
  }
}
```

### Export Saved Objects

**Via UI:**
1. Stack Management → Saved Objects
2. Select objects to export
3. Click "Export" → Download NDJSON

**Via API:**
```powershell
$auth = [System.Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes("elastic:elasticpass"))
Invoke-WebRequest -Uri "http://localhost:5601/kibana/api/saved_objects/_export" `
  -Method Post `
  -Headers @{ 'kbn-xsrf' = 'true'; 'Authorization' = "Basic $auth" } `
  -ContentType "application/json" `
  -Body '{"type":"search","includeReferencesDeep":true}' `
  -OutFile "saved_searches_export.ndjson"
```

---

## Troubleshooting

### Import Failed: Missing References

**Symptom:**
```json
{
  "error": {
    "type": "missing_references",
    "references": [{"type": "index-pattern", "id": "old-id"}]
  }
}
```

**Solution:** Update the saved search NDJSON to reference the correct index pattern ID:
1. Import data view first
2. Note the `destinationId` from the response
3. Update saved search `references[0].id` to match
4. Re-import saved search

### Data View Shows No Data

**Check index exists:**
```powershell
docker exec applylens-api-prod curl -s http://elasticsearch:9200/_cat/indices/gmail_emails-*?v
```

**Check index has documents:**
```powershell
docker exec applylens-api-prod curl -s http://elasticsearch:9200/gmail_emails/_count
```

**Refresh field list:**
1. Stack Management → Data Views
2. Select "ApplyLens Emails"
3. Click "Refresh field list"

### 404 Not Found on API Calls

**Issue:** Kibana base path not included in URL

**Solution:** Use `/kibana/api/...` instead of `/api/...`
```
Correct:   http://localhost:5601/kibana/api/saved_objects/_import
Incorrect: http://localhost:5601/api/saved_objects/_import
```

### Authentication Failed

**Check credentials:**
```powershell
Get-Content .env | Select-String "ELASTIC_PASSWORD"
```

**Test authentication:**
```powershell
$auth = [System.Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes("elastic:elasticpass"))
Invoke-WebRequest -Uri "http://localhost:5601/kibana/api/status" `
  -Headers @{ 'Authorization' = "Basic $auth" }
```

---

## Files Created

| File | Purpose | Size |
|------|---------|------|
| `infra/kibana/emails_index_pattern.ndjson` | Data view definition | ~250 B |
| `infra/kibana/emails_saved_search.ndjson` | Saved search definition | ~700 B |
| `scripts/kibana-import.ps1` | PowerShell import script | ~1.5 KB |
| `scripts/kibana-import.sh` | Bash import script | ~600 B |
| `docs/KIBANA_SETUP_2025-10-20.md` | This documentation | ~8 KB |

---

## Next Steps

### Optional Enhancements

1. **Create Visualizations**
   - Email volume over time (bar chart)
   - Top senders (pie chart)
   - Interview vs offer ratio (metric)
   - Label distribution (tag cloud)

2. **Build Dashboard**
   - Combine visualizations
   - Add filters and controls
   - Set auto-refresh

3. **Set Up Alerts**
   - Alert on new interview emails
   - Monitor email volume spikes
   - Track offer acceptance rate

4. **Add More Saved Searches**
   - Unread emails
   - Emails by label
   - Thread conversations
   - Failed processing (has `_ingest_error`)

---

## Configuration Notes

### Kibana Base Path
Kibana is configured with `server.basePath: "/kibana"` in `infra/kibana/kibana.yml`.

All API calls must include `/kibana` prefix:
- ✅ `http://localhost:5601/kibana/api/...`
- ❌ `http://localhost:5601/api/...`

### Security
- Authentication: Basic Auth (elastic user)
- Password: Configured in `.env` as `ELASTIC_PASSWORD`
- Default: `elasticpass`

### Time Field
The data view uses `received_at` as the time field. This enables:
- Time range filtering
- Time series visualizations
- Date histogram aggregations

---

## Related Documentation

- **[EMAIL_PIPELINE_SETUP_2025-10-20.md](EMAIL_PIPELINE_SETUP_2025-10-20.md)** - Email ingest pipeline setup
- **[EMAIL_INFRASTRUCTURE_APPLIED_2025-10-20.md](EMAIL_INFRASTRUCTURE_APPLIED_2025-10-20.md)** - Infrastructure summary
- **[DOC_INDEX.md](DOC_INDEX.md)** - Documentation index

---

**Status:** ✅ Production Ready  
**Kibana Access:** http://localhost:5601/kibana  
**Credentials:** elastic / elasticpass
