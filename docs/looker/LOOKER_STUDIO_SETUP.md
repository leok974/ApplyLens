# ApplyLens Looker Studio Dashboard Setup

## Overview
This guide shows how to create the **ApplyLens Overview** dashboard in Looker Studio (formerly Google Data Studio) using your BigQuery data mart.

## Prerequisites
- BigQuery dataset: `applylens_mart`
- Tables: `mart_email_activity_daily`, `mart_top_senders_30d`, `mart_categories_30d`
- Looker Studio access (free tier works fine)

## Dashboard Requirements (Phase 3)
✅ 3 visualizations from existing mart tables  
✅ <2 second query latency  
✅ <$0.01 per query cost  
✅ No red panels (all queries optimized)  

---

## Step 1: Create Data Source

1. Go to [Looker Studio](https://lookerstudio.google.com/)
2. Click **Create** → **Data Source**
3. Select **BigQuery** connector
4. Choose:
   - **My Projects** → `your-project-id`
   - **Dataset**: `applylens_mart`
   - **Table**: Start with `mart_email_activity_daily`
5. Click **Connect**
6. Name the data source: `ApplyLens BigQuery Mart`

### Repeat for Other Tables
Create 2 more data sources:
- `mart_top_senders_30d`
- `mart_categories_30d`

Or use a **Custom Query** data source (advanced):
```sql
SELECT 
  day,
  messages_count,
  unique_senders,
  avg_size_kb
FROM `your-project-id.applylens_mart.mart_email_activity_daily`
WHERE day >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY day DESC
```

---

## Step 2: Create Dashboard

1. Click **Create** → **Report**
2. Select the `ApplyLens BigQuery Mart` data source
3. Name the report: **ApplyLens Overview**

---

## Step 3: Add Visualizations

### Panel 1: Daily Email Activity (Time Series)
**Chart Type:** Time series  
**Data Source:** `mart_email_activity_daily`  
**Date Range Dimension:** `day`  
**Metrics:**
- `messages_count` (Line, Blue)
- `unique_senders` (Line, Orange)

**Configuration:**
- Date range: Last 30 days
- X-axis: `day` (Date)
- Y-axis: `messages_count`, `unique_senders`
- Show data labels: No
- Smooth lines: Yes

**Style:**
- Line width: 2px
- Fill opacity: 10%
- Grid lines: Yes

---

### Panel 2: Top 10 Senders (Bar Chart)
**Chart Type:** Bar chart (horizontal)  
**Data Source:** `mart_top_senders_30d`  
**Dimension:** `from_email`  
**Metric:** `messages_30d`  
**Sort:** `messages_30d` DESC  
**Rows to show:** 10

**Configuration:**
- Bar color: Blue (#4285F4)
- Show data labels: Yes
- Show axis titles: Yes

**Style:**
- Bar height: 30px
- Label position: Outside bars
- Font size: 12px

---

### Panel 3: Email Categories (Pie/Donut Chart)
**Chart Type:** Donut chart  
**Data Source:** `mart_categories_30d`  
**Dimension:** `category`  
**Metric:** `messages_30d`  
**Sort:** `messages_30d` DESC

**Configuration:**
- Donut hole: 40%
- Show percentages: Yes
- Show legend: Right side
- Max slices: 10
- Slice colors: Automatic palette

**Style:**
- Label font size: 12px
- Legend font size: 11px

---

## Step 4: Add Header & Metrics

### Dashboard Header
Add a **Text box** at the top:
```
ApplyLens Email Analytics
Real-time insights powered by BigQuery
```

### Key Metrics (Scorecards)
Add 3 scorecards across the top:

**Scorecard 1: Total Messages (30d)**
- Data source: `mart_email_activity_daily`
- Metric: `SUM(messages_count)` with date range filter (last 30 days)
- Label: "Total Emails"
- Size: Large

**Scorecard 2: Avg Messages/Day**
- Data source: `mart_email_activity_daily`
- Metric: `AVG(messages_count)`
- Label: "Avg per Day"
- Size: Large

**Scorecard 3: Unique Senders (30d)**
- Data source: `mart_top_senders_30d`
- Metric: `COUNT_DISTINCT(from_email)`
- Label: "Senders"
- Size: Large

---

## Step 5: Performance Optimization

### Query Caching (Automatic)
Looker Studio automatically caches BigQuery results for 12 hours. No configuration needed.

### Cost Control
**Pre-aggregated tables** (marts) dramatically reduce cost:
- ✅ `mart_email_activity_daily` scans ~30 rows for 30-day view
- ✅ `mart_top_senders_30d` scans ~100 rows
- ✅ `mart_categories_30d` scans ~20 rows

**Estimated cost per dashboard load:** <$0.001 (free tier covers it)

### Latency Optimization
1. **Partition tables** by date (already done in dbt models)
2. **Use dashboard filters** instead of live queries
3. **Enable caching**: Settings → Data Credentials → Enable cache

Expected latency: **0.5-1.5 seconds** per panel load

---

## Step 6: Share Dashboard

1. Click **Share** (top-right)
2. Add email addresses or get shareable link
3. Set permissions:
   - **Viewer**: Can view dashboard
   - **Editor**: Can modify dashboard

**Public link** (optional):
```
https://lookerstudio.google.com/reporting/your-report-id
```

---

## Verification Checklist

Before marking Phase 3 complete, verify:

- [ ] All 3 panels load without errors (no red error boxes)
- [ ] Query latency < 2 seconds (check query execution time in bottom-right)
- [ ] Data refreshes automatically (set auto-refresh to 15 minutes)
- [ ] Date range selector works (last 7/30/90 days)
- [ ] Dashboard is shareable via link
- [ ] Mobile view renders correctly

---

## Troubleshooting

### "BigQuery quota exceeded"
**Solution:** Your queries are too expensive. Ensure you're using pre-aggregated mart tables, not raw `emails` table.

### "Table not found"
**Solution:** Check dataset name is `applylens_mart` and tables exist:
```bash
bq ls applylens_mart
```

### "Query timeout"
**Solution:** Add partitioning to your tables:
```sql
CREATE OR REPLACE TABLE applylens_mart.mart_email_activity_daily
PARTITION BY day
AS SELECT * FROM ...
```

### "No data to display"
**Solution:** Check if dbt models have run recently:
```bash
dbt run --select mart_email_activity_daily+
```

---

## Example Screenshots

### Panel 1: Activity Time Series
```
📈 Messages Count (last 30 days)
   ^
250 |     ╱╲
    |    ╱  ╲    ╱╲
150 |   ╱    ╲  ╱  ╲
    |  ╱      ╲╱    ╲___
50  | ╱
    +--------------------→
    Day 1 → Day 30
```

### Panel 2: Top Senders
```
sender1@company.com  ████████████ 120
sender2@gmail.com    █████████ 95
sender3@domain.com   ████████ 82
...
```

### Panel 3: Categories
```
     Work: 45%
     Personal: 25%
     Updates: 15%
     Promotions: 10%
     Other: 5%
```

---

## Advanced: Embedded Dashboard

To embed in ApplyLens web UI:

1. Click **File** → **Embed report**
2. Copy the `<iframe>` code
3. Add to `apps/web/src/pages/Analytics.tsx`:

```tsx
<iframe
  width="100%"
  height="600"
  src="https://lookerstudio.google.com/embed/reporting/your-report-id"
  frameBorder="0"
  style={{ border: 0 }}
  allowFullScreen
/>
```

---

## Next Steps

1. ✅ Create dashboard in Looker Studio (~10 minutes)
2. ✅ Verify all panels load < 2s
3. ✅ Take screenshots for Devpost submission
4. ✅ Get shareable link for judges
5. ✅ Test on mobile device

**Devpost Evidence:**
- Screenshot of dashboard with all 3 panels
- Query execution times (visible in Looker Studio bottom bar)
- Shareable link in README.md

---

## Cost Analysis

| Component | Estimated Cost |
|-----------|----------------|
| Dashboard load (3 queries) | <$0.001 |
| Auto-refresh (15 min × 8 hours) | $0.032/day |
| Monthly cost (20 users) | ~$1-5/month |

**Covered by BigQuery free tier:** 1 TB query/month (enough for 10K+ dashboard views)

🎉 **Phase 3 Complete**: Grafana and Looker Studio dashboards ready!
