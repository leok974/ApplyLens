# Fivetran → BigQuery Setup for ApplyLens

This guide walks you through setting up Fivetran to sync ApplyLens PostgreSQL data to BigQuery for analytics.

---

## 🎯 Overview

**Data Flow:**

```text
Postgres (ApplyLens DB) → Fivetran Connector → BigQuery (dataset: applylens)
```text

**Sync Frequency:** Hourly (configurable to 30 minutes)  
**Method:** HVR (High Volume Replication) disabled for cost  
**Timezone:** UTC

---

## 📋 Prerequisites

1. **BigQuery Project**
   - Google Cloud project with BigQuery API enabled
   - Dataset `applylens` created (location: `US`)
   - Service account with BigQuery Data Editor role

2. **Fivetran Account**
   - Free tier supports 1 destination + limited connectors
   - Standard tier recommended for production

3. **ApplyLens Database Access**
   - PostgreSQL connection details (host, port, database, user, password)
   - Database user with read permissions on target tables
   - Optional: IP allowlist for Fivetran egress IPs

---

## 🚀 Step 1: Create BigQuery Dataset

### Via Console

1. Go to <https://console.cloud.google.com/bigquery>
2. Select your project
3. Click **Create Dataset**
   - Dataset ID: `applylens`
   - Location: `US` (multi-region)
   - Default table expiration: Never
   - Enable encryption: Google-managed key
4. Click **Create Dataset**

### Via gcloud CLI

```bash
# Authenticate
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Create dataset
bq mk --location=US --dataset applylens
```text

---

## 🔌 Step 2: Set Up Fivetran Destination

### 1. Create BigQuery Destination

1. Log in to <https://fivetran.com/dashboard>
2. Navigate to **Destinations** → **Add Destination**
3. Select **Google BigQuery**
4. Configure:
   - **Destination Name:** `ApplyLens Analytics`
   - **Authentication:** Google OAuth (recommended) or Service Account JSON
   - **Project ID:** Your GCP project ID
   - **Dataset:** `applylens`
   - **Location:** `US`
5. Click **Save & Test**
6. Verify connection successful

### 2. Service Account Method (Alternative)

```bash
# Create service account
gcloud iam service-accounts create fivetran-applylens \
  --display-name="Fivetran ApplyLens Sync"

# Grant BigQuery permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:fivetran-applylens@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:fivetran-applylens@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

# Create and download key
gcloud iam service-accounts keys create fivetran-key.json \
  --iam-account=fivetran-applylens@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Upload JSON to Fivetran when creating destination
```text

---

## 🗄️ Step 3: Configure PostgreSQL Connector

### 1. Prepare Database User

```sql
-- Create read-only user for Fivetran
CREATE USER fivetran_user WITH PASSWORD 'your_secure_password';

-- Grant schema access
GRANT USAGE ON SCHEMA public TO fivetran_user;

-- Grant table read permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO fivetran_user;

-- Grant future tables access
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
  GRANT SELECT ON TABLES TO fivetran_user;

-- Verify access
\c applylens fivetran_user
SELECT count(*) FROM emails;
SELECT count(*) FROM applications;
```text

### 2. Optional: IP Allowlist for Security

If using Cloudflare or database firewall, allowlist Fivetran IPs:

**Fivetran IP Ranges (as of 2025):**

```text
52.0.2.4/32
35.234.176.144/29
35.227.135.0/29
# Check https://fivetran.com/docs/getting-started/ips for latest
```text

**PostgreSQL pg_hba.conf:**

```conf
# Fivetran access
host    applylens    fivetran_user    52.0.2.4/32    md5
host    applylens    fivetran_user    35.234.176.144/29    md5
host    applylens    fivetran_user    35.227.135.0/29    md5
```text

### 3. Create Connector in Fivetran

1. In Fivetran dashboard: **Connectors** → **Add Connector**
2. Search for **PostgreSQL**
3. Select destination: `ApplyLens Analytics`
4. Configure connection:
   - **Host:** Your database host (e.g., `db.applylens.com`)
   - **Port:** `5432`
   - **Database:** `applylens`
   - **User:** `fivetran_user`
   - **Password:** Your secure password
   - **Connection Method:**
     - **Direct** (if publicly accessible)
     - **SSH Tunnel** (recommended for security)
     - **Reverse SSH Tunnel** (for private networks)

5. **Test Connection** → Should show green checkmark

### 4. Select Tables to Sync

**Minimal Required Tables:**

- ✅ `emails` - Core email data with risk scores
- ✅ `applications` - Job application tracking (if present)

**Optional Tables for Enhanced Analytics:**

- `users` - User information
- `oauth_google` - Gmail connection metadata
- `gmail_tokens` - Token refresh timing
- `reply_metrics` - Time-to-reply data

**Column Selection for `emails`:**

```text
✅ id (PK)
✅ received_at (timestamp)
✅ sender (text)
✅ subject (text)
✅ body (text) - optional, may be large
✅ risk_score (float)
✅ category (text)
✅ expires_at (timestamp)
✅ features_json (jsonb)
✅ created_at (timestamp)
✅ updated_at (timestamp)
```text

**Column Selection for `applications`:**

```text
✅ id (PK)
✅ company (text)
✅ role (text)
✅ source (text)
✅ created_at (timestamp)
✅ status (text)
✅ user_id (FK)
```text

### 5. Configure Sync Settings

- **Sync Frequency:**
  - Development: Every 6 hours
  - Production: Every 1 hour (or 30 minutes)
- **HVR (High Volume Replication):** **Disabled** (to reduce costs)
- **Schema Changes:** Auto-detect (Fivetran handles new columns)
- **Historical Sync:** Full table on first run

### 6. Start Initial Sync

1. Click **Save & Test**
2. Fivetran validates connection and begins initial sync
3. Monitor progress in **Connector Dashboard**
4. First sync may take 10-60 minutes depending on data volume

**Verify Sync:**

```sql
-- In BigQuery, check synced tables
SELECT table_name, row_count, size_bytes
FROM applylens.__TABLES__
ORDER BY table_name;

-- Check emails table
SELECT count(*) as email_count,
       min(received_at) as earliest,
       max(received_at) as latest
FROM applylens.public_emails;

-- Check risk score distribution
SELECT 
  CASE 
    WHEN risk_score IS NULL THEN 'null'
    WHEN risk_score < 30 THEN 'low'
    WHEN risk_score < 60 THEN 'medium'
    WHEN risk_score < 90 THEN 'high'
    ELSE 'critical'
  END as risk_bucket,
  COUNT(*) as count
FROM applylens.public_emails
GROUP BY risk_bucket
ORDER BY risk_bucket;
```text

---

## 📊 Optional: Add Google Search Console Connector

### 1. Set Up GSC in Fivetran

1. **Connectors** → **Add Connector** → **Google Search Console**
2. Authenticate with Google account that has GSC access
3. Select property: `https://applylens.com`
4. Destination: `ApplyLens Analytics`
5. Tables synced:
   - `search_analytics_by_page`
   - `search_analytics_by_query`
   - `search_analytics_by_country`

### 2. Join GSC with Email Data (dbt)

```sql
-- Example: emails from recruiters at companies we rank for
WITH gsc_domains AS (
  SELECT DISTINCT
    REGEXP_EXTRACT(page, r'https?://([^/]+)') as domain,
    SUM(clicks) as total_clicks
  FROM applylens.google_search_console_search_analytics_by_page
  WHERE query LIKE '%job%' OR query LIKE '%career%'
  GROUP BY domain
)
SELECT 
  e.sender,
  REGEXP_EXTRACT(e.sender, r'@(.+)$') as sender_domain,
  g.total_clicks,
  COUNT(*) as email_count,
  AVG(e.risk_score) as avg_risk
FROM applylens.public_emails e
LEFT JOIN gsc_domains g ON REGEXP_EXTRACT(e.sender, r'@(.+)$') = g.domain
WHERE e.category = 'recruiter'
GROUP BY e.sender, sender_domain, g.total_clicks
HAVING g.total_clicks > 0
ORDER BY g.total_clicks DESC;
```text

---

## 📈 Optional: Add Google Analytics 4 Connector

### 1. Set Up GA4 in Fivetran

1. **Connectors** → **Add Connector** → **Google Analytics 4**
2. Authenticate and select property
3. Destination: `ApplyLens Analytics`
4. Tables synced:
   - `events` - User interactions
   - `user_properties` - User attributes
   - `items` - E-commerce (if applicable)

### 2. Join GA4 with Applications (dbt)

```sql
-- Track application page views → actual applications
WITH application_events AS (
  SELECT 
    user_pseudo_id,
    event_date,
    COUNT(*) as page_views
  FROM applylens.google_analytics_4_events
  WHERE event_name = 'page_view'
    AND page_location LIKE '%/applications%'
  GROUP BY user_pseudo_id, event_date
)
SELECT 
  ae.event_date,
  ae.page_views,
  COUNT(DISTINCT a.id) as applications_created,
  SAFE_DIVIDE(COUNT(DISTINCT a.id), SUM(ae.page_views)) as conversion_rate
FROM application_events ae
LEFT JOIN applylens.public_applications a 
  ON DATE(a.created_at) = PARSE_DATE('%Y%m%d', ae.event_date)
GROUP BY ae.event_date, ae.page_views
ORDER BY ae.event_date DESC;
```text

---

## 🔐 Security Best Practices

### Database Credentials

- ✅ Use read-only user (`fivetran_user`)
- ✅ Rotate password quarterly
- ✅ Restrict to specific tables (GRANT SELECT only)
- ✅ Monitor query logs for anomalies

### Network Security

- ✅ IP allowlist Fivetran egress IPs
- ✅ Use SSL/TLS for database connections
- ✅ SSH tunnel for private networks
- ❌ Avoid exposing database publicly

### BigQuery Access

- ✅ Least privilege IAM roles
- ✅ Service account for automation
- ✅ Audit logs enabled
- ✅ Data encryption at rest (default)

---

## 🔧 Troubleshooting

### Connection Failed

```bash
# Test database connectivity
psql -h YOUR_HOST -U fivetran_user -d applylens -c "SELECT version();"

# Check firewall rules
telnet YOUR_HOST 5432

# Verify user permissions
psql -U fivetran_user -d applylens -c "\dt"
```text

### Sync Stalled

1. Check **Connector Logs** in Fivetran dashboard
2. Common issues:
   - Table schema changes (Fivetran auto-detects)
   - Network timeouts (check connectivity)
   - Permission errors (verify GRANT SELECT)
3. **Manual Resync:** Connector → **Re-sync** → Select tables

### Slow Sync Performance

- Reduce sync frequency (6h instead of 1h)
- Exclude large columns (e.g., `body` field)
- Enable HVR for large tables (increases cost)
- Contact Fivetran support for optimization

### BigQuery Quota Exceeded

```bash
# Check quota usage
gcloud alpha billing quotas list \
  --project=YOUR_PROJECT_ID \
  --service=bigquery.googleapis.com

# Request quota increase if needed
# https://console.cloud.google.com/iam-admin/quotas
```text

---

## 📊 Monitoring Sync Health

### Fivetran Dashboard

- **Last Successful Sync:** Should be < 2 hours ago
- **Rows Synced:** Should match table counts
- **Errors:** Should be 0

### BigQuery Monitoring

```sql
-- Check last updated timestamp
SELECT 
  table_name,
  TIMESTAMP_MILLIS(creation_time) as created,
  TIMESTAMP_MILLIS(last_modified_time) as last_updated,
  row_count
FROM applylens.__TABLES__
ORDER BY last_modified_time DESC;

-- Compare counts with source
SELECT 'BigQuery' as source, COUNT(*) as count FROM applylens.public_emails
UNION ALL
SELECT 'Expected' as source, 12345 as count;  -- Update from Postgres count
```text

---

## 📚 Next Steps

After Fivetran is syncing successfully:

1. **Set up dbt** for data transformations
   - See: `analytics/dbt/README.md`
2. **Create mart models** for analytics
   - Risk trends, parity drift, SLO tracking
3. **Export to Elasticsearch** for Kibana
   - See: `analytics/export/export_to_es.py`
4. **Build Kibana dashboards**
   - See: `services/api/dashboards/analytics-overview.ndjson`

---

## 🔗 Resources

- [Fivetran Docs](https://fivetran.com/docs)
- [Fivetran PostgreSQL Connector](https://fivetran.com/docs/databases/postgresql)
- [Fivetran IP Addresses](https://fivetran.com/docs/getting-started/ips)
- [BigQuery Quickstart](https://cloud.google.com/bigquery/docs/quickstarts)
- [dbt BigQuery Setup](https://docs.getdbt.com/reference/warehouse-setups/bigquery-setup)

---

*Last Updated: October 2025*  
*Maintainer: ApplyLens Analytics Team*
