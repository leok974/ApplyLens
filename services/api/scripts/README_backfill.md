# Backfill Bill Dates Script

## Purpose

Reprocess existing bill emails in Elasticsearch to extract due dates using the robust `due_dates.py` parser. Updates `dates[]` and `expires_at` fields for bills that are missing date information or have incorrect `expires_at` values.

## Features

- ✅ **Robust Date Extraction**: Uses same parser as email ingestion (handles multiple formats)
- ✅ **Dry Run Mode**: See what would be updated before making changes
- ✅ **Bulk Updates**: Processes documents in batches for efficiency
- ✅ **Smart Updates**: Only updates documents that have changes
- ✅ **Recomputes expires_at**: Sets to earliest due date
- ✅ **Progress Reporting**: Shows scan/update counts

## Requirements

**Elasticsearch Client Version Compatibility:**

The script requires an Elasticsearch client version that matches your server version.

- **ES Server 8.x** → Use `elasticsearch>=8.0.0,<9.0.0`
- **ES Server 9.x** → Use `elasticsearch>=9.0.0`

If you encounter version mismatch errors:

```bash
# Check your ES server version
curl http://localhost:9200

# Check your client version
python -c "import elasticsearch; print(elasticsearch.__version__)"

# Downgrade client if needed (for ES 8.x server)
pip install "elasticsearch>=8.0.0,<9.0.0"
```

## Quick Validation

Use `validate_backfill.py` to check backfill results at any time:

**Human-Readable Summary:**

```bash
python scripts/validate_backfill.py --pretty
```

**Example Output:**

```
Index: gmail_emails_v2
Missing dates[] (bills): 0
Bills with dates[]:      1243
Bills with expires_at:   1243
Verdict: OK  @ 2025-10-10T14:22:31Z
```

**PowerShell:**

```powershell
$env:ES_URL="http://localhost:9200"
$env:ES_EMAIL_INDEX="gmail_emails_v2"
python scripts/validate_backfill.py --pretty
```

**JSON Output (for automation):**

```bash
python scripts/validate_backfill.py --json
# {"index": "gmail_emails_v2", "missing_dates_count": 0, "bills_with_dates": 1243, ...}
```

**Makefile:**

```bash
make validate-backfill           # Human-readable
make validate-backfill-json      # JSON output
```

**Verdict Guide:**

- ✅ **OK**: No missing dates, all counts consistent
- ⚠️ **CHECK**: Missing dates found or data anomalies detected

**Before/After Workflow:**

Run validation before the backfill, then run it again after to prove the improvement:

```bash
# Before
make validate-backfill > before.txt

# Run backfill
make backfill-bills-live

# After
make validate-backfill > after.txt

# Compare
diff before.txt after.txt
```

## Usage

### Pre-Flight Checks

Before running the backfill, check how many bills are missing dates:

**ES|QL Query (Kibana Dev Tools):**

```sql
FROM gmail_emails_v2
| WHERE category == "bills" AND NOT _exists_:dates
| STATS missing=count()
```

**cURL:**

```bash
curl -X POST "http://localhost:9200/gmail_emails_v2/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"category": "bills"}},
          {"bool": {"must_not": {"exists": {"field": "dates"}}}}
        ]
      }
    },
    "size": 0,
    "track_total_hits": true
  }'
```

**Makefile:**

```bash
make check-bills-missing
```

### 1. Dry Run (Recommended First)

See what would be updated without making changes:

```bash
cd services/api

# Set environment variables
export DRY_RUN=1
export ES_URL="http://localhost:9200"
export ES_EMAIL_INDEX="gmail_emails_v2"

# Run script
python scripts/backfill_bill_dates.py
```

**PowerShell (Windows):**

```powershell
cd services/api

$env:DRY_RUN="1"
$env:ES_URL="http://localhost:9200"
$env:ES_EMAIL_INDEX="gmail_emails_v2"

python scripts/backfill_bill_dates.py
```

### 2. Execute Updates

After reviewing dry run results, run for real:

```bash
export DRY_RUN=0
python scripts/backfill_bill_dates.py
```

**PowerShell:**

```powershell
$env:DRY_RUN="0"
python scripts/backfill_bill_dates.py
```

### Post-Flight Verification

After running the backfill, verify the results:

**Quick Validation (Recommended):**

Use the validation script for a comprehensive health check:

```bash
# Human-readable summary
python scripts/validate_backfill.py --pretty

# JSON output (for automation)
python scripts/validate_backfill.py --json
```

**PowerShell:**

```powershell
$env:ES_URL="http://localhost:9200"
$env:ES_EMAIL_INDEX="gmail_emails_v2"
python scripts/validate_backfill.py --pretty
```

**Makefile:**

```bash
make validate-backfill           # Human-readable
make validate-backfill-json      # JSON output
```

**Example Output:**

```
Index: gmail_emails_v2
Missing dates[] (bills): 0
Bills with dates[]:      1243
Bills with expires_at:   1243
Verdict: OK  @ 2025-10-10T14:22:31Z
```

**Manual ES|QL Query (Check bills with dates and expires_at):**

```sql
FROM gmail_emails_v2
| WHERE category == "bills" AND _exists_:dates
| STATS with_expiry=count(_exists_:expires_at), total=count()
```

**Expected result:** Most/all bills should have both `dates` and `expires_at` populated.

**cURL:**

```bash
curl -X POST "http://localhost:9200/gmail_emails_v2/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"category": "bills"}},
          {"exists": {"field": "dates"}}
        ]
      }
    },
    "size": 0,
    "aggs": {
      "with_expiry": {
        "filter": {"exists": {"field": "expires_at"}}
      }
    }
  }'
```

**Makefile (legacy check):**

```bash
make check-bills-with-dates
```

**Example output:**

```
Bills with dates: 523
Bills with expires_at: 523
```

### 3. Monitor Progress

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ES_URL` | `http://localhost:9200` | Elasticsearch server URL |
| `ES_EMAIL_INDEX` | `gmail_emails_v2` | Index containing emails |
| `DRY_RUN` | `1` | Set to `0` to execute updates |
| `BATCH` | `500` | Bulk update batch size |
| `ES_API_KEY` | _(none)_ | API key if ES requires auth |

## What It Does

### 1. Scans Bills

Queries Elasticsearch for all documents where `category == "bills"`.

### 2. Extracts Dates

For each bill:

- Combines `subject` + `body_text`
- Runs `extract_due_dates()` to find dates near "due" keywords
- Supports formats: `10/15/2025`, `Oct 15, 2025`, `15 Oct 2025`, etc.

### 3. Updates Fields

- **`dates[]`**: Array of all extracted due dates (ISO 8601 format)
- **`expires_at`**: Earliest date from `dates[]` array

### 4. Smart Filtering

Only updates documents where:

- New dates were extracted, OR
- `expires_at` needs correction (earlier date found)

No update if dates are identical and `expires_at` is already correct.

## Example Output

**Dry Run:**

```
Starting backfill for index: gmail_emails_v2
Mode: DRY RUN
Batch size: 500
------------------------------------------------------------
Would update msg_001: {'dates': ['2025-10-25T00:00:00Z'], 'expires_at': '2025-10-25T00:00:00Z'}
Would update msg_002: {'dates': ['2025-11-15T00:00:00Z'], 'expires_at': '2025-11-15T00:00:00Z'}
Would update msg_003: {'expires_at': '2025-10-12T00:00:00Z'}
Processed 523 docs, updated 156 docs...
------------------------------------------------------------
Backfill (DRY RUN) completed.
Scanned: 523 bills
Updated: 156 bills
Unchanged: 367 bills
```

**Live Run:**

```
Starting backfill for index: gmail_emails_v2
Mode: LIVE UPDATE
Batch size: 500
------------------------------------------------------------
Processed 523 docs, updated 156 docs...
------------------------------------------------------------
Backfill completed.
Scanned: 523 bills
Updated: 156 bills
Unchanged: 367 bills
```

## Testing

Unit tests verify the transformation logic:

```bash
cd services/api
pytest tests/unit/test_backfill_transform.py -v
```

**Test Coverage:**

- ✅ Date extraction from body text
- ✅ Earliest date selection for expires_at
- ✅ Respecting existing earlier expires_at
- ✅ Updating when new date is earlier
- ✅ No-op when data is identical
- ✅ Multiple date handling
- ✅ Date deduplication
- ✅ Subject line extraction
- ✅ Year inference from received_at
- ✅ Recomputing expires_at from existing dates

**All 13 tests passing** ✅

## When to Run

### Initial Backfill

Run after deploying the due date extraction feature to populate dates for existing bills.

### After Data Issues

If you discover bills with incorrect `expires_at` values, run backfill to recompute.

### After Parser Improvements

If the date extraction regex patterns are improved, rerun to catch previously missed dates.

## Performance

- **Scan rate**: ~1000-2000 docs/sec (ES dependent)
- **Update rate**: ~500-1000 docs/sec (batch dependent)
- **Memory**: Minimal (streaming scan, batched updates)

**Estimated time for 10,000 bills:**

- Scan: ~5-10 seconds
- Update (if all need updates): ~10-20 seconds
- **Total**: < 30 seconds

## Safety Features

### 1. Dry Run Default

`DRY_RUN=1` by default prevents accidental updates.

### 2. Preserves Earlier Dates

If existing `expires_at` is earlier than extracted dates, it keeps the earlier value.

### 3. Idempotent

Safe to run multiple times - only updates when changes detected.

### 4. Batch Limiting

Uses `BATCH` size to limit memory usage and allow progress tracking.

## Troubleshooting

### No bills found

**Check category field:**

```bash
curl "http://localhost:9200/gmail_emails_v2/_search?pretty" -H "Content-Type: application/json" -d '{
  "query": {"term": {"category": "bills"}},
  "size": 1
}'
```

**Possible causes:**

- Index name incorrect (`ES_EMAIL_INDEX`)
- Bills not classified yet (run classification first)
- No bills in index

### No updates detected

**Possible causes:**

- Dates already extracted by email ingestion
- No "due" keywords in bill text
- Date format not supported by regex

**Verify:**

```bash
# Check if dates field exists
curl "http://localhost:9200/gmail_emails_v2/_search?pretty" -d '{
  "query": {"term": {"category": "bills"}},
  "_source": ["dates", "expires_at"],
  "size": 5
}'
```

### Elasticsearch version mismatch

**Error:** `Accept version must be either version 8 or 7, but found 9`

**Solution:** Install matching ES client version:

```bash
# For ES 8.x server
pip install "elasticsearch>=8.0.0,<9.0.0"

# Check versions
curl http://localhost:9200  # Server version
python -c "import elasticsearch; print(elasticsearch.__version__)"  # Client version
```

### Connection refused

**Check ES is running:**

```bash
docker-compose ps es
curl http://localhost:9200
```

**Check ES_URL:**

```bash
echo $ES_URL  # Should match ES server address
```

## Integration

### Related Files

- **Parser**: `app/ingest/due_dates.py` - Robust date extraction
- **Tests**: `tests/unit/test_backfill_transform.py` - Transformation logic tests
- **Ingestion**: `app/gmail_service.py` - Email ingestion with date extraction
- **Pipeline**: `infra/es/pipelines/emails_due_simple.json` - ES fallback extraction

### After Backfill

1. **Verify updates:**

   ```bash
   curl "http://localhost:9200/gmail_emails_v2/_search?pretty" -d '{
     "query": {"exists": {"field": "dates"}},
     "size": 5
   }'
   ```

2. **Test NL queries:**
   - "Show me bills due before Friday"
   - "Bills due this week"

3. **Check Kibana dashboard:**
   - Open: <http://localhost:5601>
   - View: "Bills due per day (next 7d)"

## Examples

### Example 1: First Time Backfill

```bash
# Dry run to see scope
DRY_RUN=1 python scripts/backfill_bill_dates.py

# Output: Would update 234 bills

# Execute
DRY_RUN=0 python scripts/backfill_bill_dates.py

# Output: Updated 234 bills
```

### Example 2: Recompute expires_at Only

Some bills have dates but wrong `expires_at`:

```bash
# Run backfill - will recompute expires_at from existing dates
DRY_RUN=0 python scripts/backfill_bill_dates.py

# Output: Updated 45 bills (dates unchanged, expires_at corrected)
```

### Example 3: After Parser Improvement

You improved the regex to catch more date formats:

```bash
# Backfill will extract newly-detectable dates
DRY_RUN=0 python scripts/backfill_bill_dates.py

# Output: Updated 89 bills (new dates extracted)
```

## Code Structure

```python
# Main flow
def run():
    1. Create ES client
    2. Scan all bills (helpers.scan)
    3. For each hit:
        - transform(doc)  # Extract dates
        - Add to batch
        - Bulk update when batch full
    4. Final batch update
    5. Report stats

# Transformation
def transform(doc):
    1. Extract subject + body_text
    2. Call extract_due_dates()
    3. Compute earliest date
    4. Compare with existing expires_at
    5. Return update dict or None

# Date extraction
extract_due_dates(text, received_at)
    -> Regex finds dates near "due"
    -> Parse into datetime
    -> Format as ISO 8601
    -> Deduplicate and sort
```

## Future Enhancements

- [ ] Add `--limit` parameter to process subset
- [ ] Add `--force` to update even if no changes
- [ ] Support filtering by date range
- [ ] Add progress bar for large indexes
- [ ] Export report of updated document IDs
- [ ] Parallel processing for large datasets

## See Also

- **Feature Docs**: `app/ingest/README_due_dates.md`
- **Deployment**: `DEPLOYMENT_due_dates.md`
- **Parser Tests**: `tests/unit/test_due_date_extractor.py`
