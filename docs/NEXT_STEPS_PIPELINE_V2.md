# Next Steps: Pipeline v2 Deployment — October 20, 2025

**Status:** ✅ Infrastructure validated and ready  
**Current State:** Existing emails need migration to populate v2 flags  
**Goal:** Get pipeline v2 smart flags working with your existing data

---

## Current Situation

### What You Have ✅
- ✅ Pipeline v2 uploaded (`applylens_emails_v2`)
- ✅ Index template configured for v2
- ✅ CI guard script tested
- ✅ Existing emails in `gmail_emails` index (~1,875 docs)
- ✅ Documentation complete

### What's Missing 🔄
- 🔄 Existing emails don't have v2 smart flags
- 🔄 Need to reindex through pipeline v2

**Why?** Pipeline v2 only processes NEW documents or documents reindexed through it. Your existing emails were processed before v2 existed.

---

## Option 1: Quick Test (Recommended First)

Test pipeline v2 with a sample document to verify everything works:

```powershell
# Test pipeline v2 with sample data
curl -X POST "http://localhost:9200/_ingest/pipeline/applylens_emails_v2/_simulate" `
  -H 'Content-Type: application/json' `
  -d '{
  "docs": [{
    "_source": {
      "from": "recruiter@acme.com",
      "to": "your.email@example.com",
      "subject": "Interview Invitation - Senior Engineer",
      "body_html": "<p>Hi! I have a calendar invite attached for our interview. Looking forward to speaking with you about the Senior Engineer role at Acme Corp.</p>",
      "body_text": "Hi! I have a calendar invite attached for our interview. Looking forward to speaking with you about the Senior Engineer role at Acme Corp.",
      "received_at": "2025-10-20T10:00:00Z",
      "gmail_id": "test123",
      "thread_id": "thread123",
      "labels": ["INBOX", "IMPORTANT"]
    }
  }]
}'
```

**Expected Output:**
```json
{
  "from": "recruiter@acme.com",
  "subject": "Interview Invitation - Senior Engineer",
  "is_recruiter": true,
  "has_calendar_invite": true,
  "has_attachment": false,
  "company_guess": "acme",
  "is_interview": true,
  "is_offer": false,
  "labels_norm": ["inbox", "important"]
}
```

---

## Option 2: Reindex Existing Data (Recommended)

Migrate your existing emails through pipeline v2 to populate all smart flags.

### Using the Automated Script

```powershell
# Run the reindex script
.\scripts\reindex_to_pipeline_v2.ps1
```

**What it does:**
1. ✅ Checks source index count (~1,875 docs)
2. ✅ Creates new destination index `gmail_emails_v2_migrated`
3. ✅ Reindexes all documents through pipeline v2
4. ✅ Verifies counts match
5. ✅ Checks that v2 flags are present

**Time:** ~30-60 seconds for 1,875 documents

### Manual Reindex (Alternative)

If you prefer to run commands manually:

```powershell
# 1. Create destination index
curl -X PUT "http://localhost:9200/gmail_emails_v2_migrated" `
  -H 'Content-Type: application/json' `
  -d '{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index.default_pipeline": "applylens_emails_v2"
  }
}'

# 2. Reindex through pipeline v2
curl -X POST "http://localhost:9200/_reindex?wait_for_completion=true" `
  -H 'Content-Type: application/json' `
  -d '{
  "source": {
    "index": "gmail_emails"
  },
  "dest": {
    "index": "gmail_emails_v2_migrated",
    "pipeline": "applylens_emails_v2"
  }
}'

# 3. Verify counts match
curl "http://localhost:9200/gmail_emails/_count"
curl "http://localhost:9200/gmail_emails_v2_migrated/_count"

# 4. Check sample document has v2 flags
curl "http://localhost:9200/gmail_emails_v2_migrated/_search?size=1" | jq '.hits.hits[]._source | {from, subject, is_recruiter, has_calendar_invite, has_attachment, company_guess}'
```

---

## Option 3: Test Queries

Once reindexed, test the smart flag queries:

```powershell
# Run automated query tests
.\scripts\test_pipeline_v2_queries.ps1
```

**What it tests:**
1. ✅ Recruiter emails (`is_recruiter:true`)
2. ✅ Interview scheduling (`is_recruiter:true AND has_calendar_invite:true`)
3. ✅ Active opportunities (`(is_offer:true OR is_interview:true) AND archived:false`)
4. ✅ Emails with attachments (`has_attachment:true`)
5. ✅ Company-specific emails (`company_guess:*`)
6. ✅ Interview emails (`is_interview:true`)
7. ✅ Offer emails (`is_offer:true`)
8. ✅ Complete interview packages (all flags combined)

---

## Option 4: Query in Kibana

### Create Data View

1. Navigate to **Kibana** → **Management** → **Data Views**
2. Click **Create data view**
3. Name: `Gmail Emails v2`
4. Index pattern: `gmail_emails_v2_migrated`
5. Time field: `received_at`
6. Save

### Run KQL Queries

Navigate to **Discover** and try these queries:

```kql
# Find recruiter emails
is_recruiter:true

# Interview scheduling
is_recruiter:true and has_calendar_invite:true

# Active opportunities
(is_offer:true or is_interview:true) and archived:false

# Company-specific search
company_guess:google

# High-priority interviews
is_interview:true and has_calendar_invite:true and labels_norm:"important"

# Recent offers
is_offer:true and received_at >= now-7d

# Emails with attachments from specific company
company_guess:acme and has_attachment:true
```

---

## Option 5: Update Ingestion Script

Update `analytics/ingest/gmail_backfill_to_es_bq.py` to use pipeline v2 for future ingestion:

### Current Code (Line 14):
```python
ES_INDEX = os.getenv("ES_EMAIL_INDEX", "emails_v1-000001")
```

### Update To:
```python
ES_INDEX = os.getenv("ES_EMAIL_INDEX", "gmail_emails_v2_migrated")
# Or use the gmail_emails alias after setting it to point to v2 index
```

### Better: Use the Alias Pattern

Instead of hardcoding the index, use the ILM-managed alias:

```python
# Update the es_index function to use the write alias
def es_index(doc: dict):
    rid = doc["id"]
    # Use the write alias - ILM will manage rollovers
    index_alias = "gmail_emails"
    r = requests.post(
        f"{ES_URL}/{index_alias}/_doc/{rid}?pipeline=applylens_emails_v2&refresh=true",
        headers={"Content-Type": "application/json"},
        data=json.dumps(doc),
    )
    r.raise_for_status()
```

**Benefits:**
- ✅ ILM automatically manages index rollovers (25GB or 30 days)
- ✅ All new docs processed through v2 pipeline
- ✅ No manual index management needed

---

## Option 6: CI/CD Integration

Add the CI guard to prevent regressions:

### GitHub Actions

```yaml
# .github/workflows/validate-elasticsearch.yml
name: Validate Elasticsearch Config

on:
  push:
    paths:
      - 'infra/elasticsearch/**'
  pull_request:
    paths:
      - 'infra/elasticsearch/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests
      
      - name: Start Elasticsearch (if testing)
        run: |
          docker-compose up -d elasticsearch
          sleep 30
      
      - name: Apply templates
        run: |
          curl -X PUT "http://localhost:9200/_component_template/applylens_emails_mapping" \
            -H 'Content-Type: application/json' \
            --data-binary @infra/elasticsearch/templates/emails_component_template_mapping.json
          
          curl -X PUT "http://localhost:9200/_index_template/applylens_emails" \
            -H 'Content-Type: application/json' \
            --data-binary @infra/elasticsearch/templates/emails_index_template.json
      
      - name: Run CI Guard
        run: python scripts/test_es_template.py
```

### Local Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
if git diff --cached --name-only | grep -q "infra/elasticsearch/templates/"; then
  echo "🔍 Validating Elasticsearch templates..."
  python scripts/test_es_template.py
  if [ $? -ne 0 ]; then
    echo "❌ Template validation failed! Commit blocked."
    exit 1
  fi
  echo "✅ Templates validated"
fi
```

---

## Recommended Workflow

### Step-by-Step

1. **Test pipeline v2 (5 minutes)**
   ```powershell
   # Simulate with sample data
   curl -X POST "http://localhost:9200/_ingest/pipeline/applylens_emails_v2/_simulate" ...
   ```

2. **Reindex existing data (2 minutes)**
   ```powershell
   .\scripts\reindex_to_pipeline_v2.ps1
   ```

3. **Test queries (2 minutes)**
   ```powershell
   .\scripts\test_pipeline_v2_queries.ps1
   ```

4. **Query in Kibana (5 minutes)**
   - Create data view
   - Run KQL queries
   - Verify smart flags work

5. **Update ingestion script (5 minutes)**
   - Modify `gmail_backfill_to_es_bq.py`
   - Use pipeline parameter or alias

6. **Set up CI guard (10 minutes)**
   - Add to GitHub Actions
   - Or create pre-commit hook

**Total time: ~30 minutes**

---

## Verification Checklist

After completing the workflow:

- [ ] Pipeline v2 simulation tested successfully
- [ ] Existing data reindexed with v2 flags
- [ ] Query tests show expected results
- [ ] Kibana queries return correct documents
- [ ] Ingestion script updated for future emails
- [ ] CI guard integrated to prevent regressions
- [ ] Documentation reviewed and understood

---

## Troubleshooting

### Issue: Reindex fails with "index already exists"

**Solution:**
```powershell
# Delete the destination index and try again
curl -X DELETE "http://localhost:9200/gmail_emails_v2_migrated"
.\scripts\reindex_to_pipeline_v2.ps1
```

### Issue: v2 flags are null or missing

**Check pipeline exists:**
```powershell
curl "http://localhost:9200/_ingest/pipeline/applylens_emails_v2"
```

**Check pipeline is being used:**
```powershell
curl "http://localhost:9200/gmail_emails_v2_migrated/_settings" | jq '.[] .settings.index.default_pipeline'
```

**Verify with simulation:**
```powershell
curl -X POST "http://localhost:9200/_ingest/pipeline/applylens_emails_v2/_simulate" ...
```

### Issue: Query tests show 0 results

**Check index name:**
```powershell
# Update the script to use your actual index name
$INDEX = "gmail_emails_v2_migrated"  # in test_pipeline_v2_queries.ps1
```

**Check data exists:**
```powershell
curl "http://localhost:9200/gmail_emails_v2_migrated/_count"
```

---

## Summary

You're at the final stage! Just need to:

1. ✅ **Reindex** existing data through pipeline v2 (2 min)
2. ✅ **Test** queries to verify flags work (2 min)
3. ✅ **Update** ingestion script for future emails (5 min)
4. ✅ **Celebrate** 🎉 - Your email analytics are supercharged!

**Total time: ~10 minutes to production-ready** 🚀

---

## Related Documentation

- [Pipeline v2 Validation](./PIPELINE_V2_VALIDATION_2025-10-20.md) - Validation summary
- [Pipeline v2 Setup](./EMAIL_PIPELINE_V2_DASHBOARD_2025-10-20.md) - Complete v2 guide
- [Kibana Lens Visualizations](./KIBANA_LENS_VISUALIZATIONS_2025-10-20.md) - Create dashboards
- [Complete Infrastructure](./COMPLETE_INFRASTRUCTURE_SUMMARY_2025-10-20.md) - Full overview

---

**Ready to proceed?** Start with: `.\scripts\reindex_to_pipeline_v2.ps1` 🚀
