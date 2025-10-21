# Kibana Lens Visualizations Setup Guide

**Date:** October 20, 2025  
**ApplyLens Infrastructure Component**

---

## Overview

This guide covers creating Lens visualizations in Kibana for ApplyLens email analytics and traffic monitoring. While NDJSON imports are provided, Lens visualizations are best created through the Kibana UI due to version-specific state formats.

---

## Components Created

### 1. **Saved Search: Offers & Interviews**
- **ID:** `applylens-emails-discover-offers`
- **Title:** "ApplyLens — Emails (Offers & Interviews)"
- **Description:** Only emails detected as offers or interviews (archived filtered out)
- **Status:** ✅ **Imported Successfully**

**Columns:**
- `received_at` (160px width)
- `from` (240px width)
- `to` (240px width)
- `subject` (420px width)
- `labels_norm`
- `is_interview`
- `is_offer`

**Query:** `(is_offer:true or is_interview:true) and archived:false`

### 2. **Lens Visualization: Emails Offers vs Interviews**
- **Title:** "Emails — Offers vs Interviews (5m)"
- **Type:** Stacked Bar Chart
- **Time Interval:** 5 minutes
- **Data View:** ApplyLens Emails (`gmail_emails-*`)
- **Status:** ⚠️ **Create manually (recommended)**

### 3. **Lens Visualization: Traffic Status Codes**
- **Title:** "Traffic — 4xx / 5xx / 429 (5m)"
- **Type:** Stacked Bar Chart
- **Time Interval:** 5 minutes
- **Data View:** Logs (`logs-*`)
- **Status:** ⚠️ **Create manually (recommended)**

---

## Import Results

### Saved Search Import
```json
{
  "successCount": 1,
  "success": true,
  "successResults": [{
    "type": "search",
    "id": "applylens-emails-discover-offers",
    "meta": {
      "title": "ApplyLens — Emails (Offers & Interviews)",
      "icon": "discoverApp"
    }
  }]
}
```

✅ **Successfully imported** and ready to use!

### Lens Visualizations
⚠️ Due to version-specific Lens state formats in Kibana 8.13.4, the Lens visualizations are best created manually through the UI. Follow the instructions below.

---

## Creating Lens Visualizations Manually

### Visualization 1: Emails Offers vs Interviews

**Step 1: Open Lens**
1. Navigate to **Analytics → Visualize Library**
2. Click **Create visualization**
3. Select **Lens**

**Step 2: Select Data View**
- Choose **ApplyLens Emails** (or the data view with ID `919a7f6d-4431-451f-b5a6-7f3943524bd4`)

**Step 3: Configure Time Field**
- X-axis: `received_at`
- Interval: **5 minutes**
- Operation: **Date histogram**

**Step 4: Add Metrics**

**Metric A - Offers:**
- Function: **Count**
- Filter: `is_offer:true`
- Label: "Offers"

**Metric B - Interviews:**
- Function: **Count**
- Filter: `is_interview:true`
- Label: "Interviews"

**Step 5: Configure Visualization**
- Type: **Bar** (stacked)
- Legend: **Right side**
- Query filter: `archived:false`

**Step 6: Save**
- Title: "Emails — Offers vs Interviews (5m)"
- Description: "Stacked counts of offers vs interviews over time"

---

### Visualization 2: Traffic Status Codes

**Step 1: Open Lens**
1. Navigate to **Analytics → Visualize Library**
2. Click **Create visualization**
3. Select **Lens**

**Step 2: Select Data View**
- Choose **logs-*** (or your logs data view with `http_status` field)

**Step 3: Configure Time Field**
- X-axis: `@timestamp`
- Interval: **5 minutes**
- Operation: **Date histogram**

**Step 4: Add Metrics**

**Metric A - 4xx Errors:**
- Function: **Count**
- Filter: `http_status >= 400 and http_status < 500 and http_status != 429`
- Label: "4xx"

**Metric B - 5xx Errors:**
- Function: **Count**
- Filter: `http_status >= 500`
- Label: "5xx"

**Metric C - Rate Limiting:**
- Function: **Count**
- Filter: `http_status == 429`
- Label: "429"

**Step 5: Configure Visualization**
- Type: **Bar** (stacked)
- Legend: **Right side**
- Colors: 
  - 4xx: Orange
  - 5xx: Red
  - 429: Yellow

**Step 6: Save**
- Title: "Traffic — 4xx / 5xx / 429 (5m)"
- Description: "Stacked status codes from logs"

---

## Usage in Kibana

### Accessing Saved Search

1. Navigate to **Analytics → Discover**
2. Click the **Saved** icon (bookmark) in top toolbar
3. Select **"ApplyLens — Emails (Offers & Interviews)"**
4. The view will load with:
   - Query: `(is_offer:true or is_interview:true) and archived:false`
   - 7 columns configured
   - Sorted by `received_at` descending

### Accessing Lens Visualizations

1. Navigate to **Analytics → Visualize Library**
2. Find your saved Lens visualizations:
   - "Emails — Offers vs Interviews (5m)"
   - "Traffic — 4xx / 5xx / 429 (5m)"
3. Click to open and explore

### Adding to Dashboards

1. Open or create a dashboard
2. Click **Add from library**
3. Select your Lens visualizations
4. Arrange and resize as needed
5. Save the dashboard

---

## Example Queries

### In Saved Search

**High-priority offers:**
```kql
is_offer:true and labels_norm:important
```

**Recent interviews:**
```kql
is_interview:true and received_at >= now-7d
```

**Specific sender:**
```kql
(is_offer:true or is_interview:true) and from:*@company.com
```

---

## KQL Filter Examples for Lens

### Email Visualizations

**Only unarchived:**
```kql
archived:false
```

**Specific time range:**
```kql
received_at >= "2025-10-01" and received_at < "2025-11-01"
```

**Specific labels:**
```kql
labels_norm:inbox and not labels_norm:spam
```

### Traffic Visualizations

**Specific endpoints:**
```kql
endpoint:"/api/applications"
```

**Error spikes:**
```kql
http_status >= 400
```

**By HTTP method:**
```kql
method:"POST"
```

---

## Troubleshooting

### Issue: No data in visualization

**Cause:** Time range doesn't match your data  
**Solution:**
1. Click the time picker (top right)
2. Select "Last 30 days" or "Last 90 days"
3. Or choose absolute time range matching your data

### Issue: Missing fields

**Cause:** Data view doesn't include required fields  
**Solution:**
1. Go to **Stack Management → Data Views**
2. Select your data view
3. Click **Refresh field list**
4. Verify fields like `is_offer`, `is_interview`, `http_status` appear

### Issue: Lens shows "No results"

**Cause:** Query filter is too restrictive  
**Solution:**
1. Remove or adjust the KQL filter
2. Check that your data actually has `is_offer:true` or `is_interview:true` documents
3. Verify data has been indexed (check in Discover)

### Issue: Cannot create Lens visualization

**Cause:** Insufficient permissions  
**Solution:**
- Ensure you're logged in as `elastic` user
- Check that the data view exists and is accessible

---

## Files Created

| File | Type | Status |
|------|------|--------|
| `infra/kibana/emails_saved_search_offers.ndjson` | Saved Search | ✅ Imported |
| `infra/kibana/lens_emails_offers_interviews.ndjson` | Lens Viz | ⚠️ Create manually |
| `infra/kibana/lens_traffic_status_codes.ndjson` | Lens Viz | ⚠️ Create manually |
| `docs/KIBANA_LENS_VISUALIZATIONS_2025-10-20.md` | Documentation | ✅ Created |

---

## Next Steps

1. **Create Lens visualizations manually** using the step-by-step instructions above
2. **Create a dashboard** combining:
   - Email offers vs interviews visualization
   - Traffic status codes visualization
   - Saved searches as tables
3. **Set up alerts** (optional):
   - Alert on high offer count
   - Alert on spike in 5xx errors
   - Alert on sustained rate limiting (429s)
4. **Export visualizations** once created for backup:
   - Go to **Stack Management → Saved Objects**
   - Select your Lens visualizations
   - Click **Export** to download NDJSON

---

## Configuration Notes

### Data View Requirements

**For Email Visualizations:**
- Data view pattern: `gmail_emails-*`
- Required fields: `received_at`, `is_offer`, `is_interview`, `archived`
- Time field: `received_at`

**For Traffic Visualizations:**
- Data view pattern: `logs-*` (or your logs index)
- Required fields: `@timestamp`, `http_status`
- Time field: `@timestamp`

### Performance Tips

- Use 5-minute intervals for real-time monitoring
- Use 1-hour or 1-day intervals for long time ranges
- Apply filters to reduce data volume
- Consider using sampled data for very large datasets

---

## Access Information

**Kibana URL:** http://localhost:5601/kibana  
**Username:** elastic  
**Password:** elasticpass

**Navigation:**
- **Discover:** Analytics → Discover
- **Lens:** Analytics → Visualize Library → Create visualization → Lens
- **Dashboards:** Analytics → Dashboard
- **Data Views:** Stack Management → Data Views

---

## Related Documentation

- [Kibana Setup Guide](./KIBANA_SETUP_2025-10-20.md)
- [Email Pipeline Setup](./EMAIL_PIPELINE_SETUP_2025-10-20.md)
- [Complete Infrastructure Summary](./COMPLETE_INFRASTRUCTURE_SUMMARY_2025-10-20.md)
- [Documentation Index](./DOC_INDEX.md)

---

## Summary

✅ **Saved Search:** Successfully imported and ready to use  
⚠️ **Lens Visualizations:** Create manually using UI for best results  
📊 **Capabilities:** Real-time email analytics and traffic monitoring  
🎯 **Next:** Build dashboard combining all visualizations

**Status:** Saved search deployed, Lens visualizations documented for manual creation
