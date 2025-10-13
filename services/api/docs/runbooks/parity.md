# Parity Drift — Triage Runbook

## Alert: ParityDriftTooHigh

**Trigger:** DB↔ES parity mismatch ratio > 0.5% for 15+ minutes

**Severity:** Ticket (investigate within 2 hours)

---

## Initial Response (10 minutes)

### 1. Run Parity Check

```powershell
# Windows/PowerShell
cd D:\ApplyLens\services\api

# Full parity check with all fields
python scripts/check_parity.py `
  --fields risk_score,expires_at,category `
  --sample 1000 `
  --output parity.json `
  --csv parity.csv

# Check results
Get-Content parity.json | ConvertFrom-Json | Select-Object -ExpandProperty summary
```text

### 2. Review Mismatch Details

```powershell
# View first 10 mismatches
Get-Content parity.json | ConvertFrom-Json | Select-Object -ExpandProperty mismatches | Select-Object -First 10

# View CSV for easier analysis
Import-Csv parity.csv | Format-Table -AutoSize
```text

---

## Understanding Mismatch Types

### Float Comparison (risk_score)

- **Tolerance:** ±0.001
- **Example:** DB=42.0, ES=42.0001 → **MATCH**
- **Example:** DB=42.0, ES=45.0 → **MISMATCH**

### Date Comparison (expires_at)

- **Granularity:** Day-level only
- **Example:** DB=2025-01-15T10:30:00, ES=2025-01-15T16:45:00 → **MATCH**
- **Example:** DB=2025-01-15, ES=2025-01-16 → **MISMATCH**

### Text Comparison (category)

- **Method:** Exact string match after .strip()
- **Example:** DB="recruiter", ES="recruiter" → **MATCH**
- **Example:** DB="recruiter", ES="unknown" → **MISMATCH**

---

## Common Causes & Fixes

### 1. Stale Elasticsearch Data

**Symptoms:**

- DB has newer values
- Mismatches concentrated in recently updated records

**Fix:**

```powershell
# Reindex affected emails
cd D:\ApplyLens\services\api

# Full risk score backfill
python scripts/analyze_risk.py --backfill --batch-size 50

# Verify fix
python scripts/check_parity.py --fields risk_score --sample 100
```text

### 2. Missing ES Documents

**Symptoms:**

- Parity script shows "ES document not found"
- DB count > ES count

**Fix:**

```bash
# Check document counts
curl http://localhost:9200/emails/_count
docker-compose exec db psql -U postgres -d applylens -c "SELECT COUNT(*) FROM emails;"

# Reindex missing documents
# TODO: Add script to bulk reindex missing IDs
```text

### 3. Risk Score Computation Drift

**Symptoms:**

- Same input data → different risk scores in DB vs ES
- Pattern across many records

**Investigation:**

```powershell
# Find specific email with mismatch
$email_id = "abc123"

# Check DB value
docker-compose exec db psql -U postgres -d applylens -c "
  SELECT id, sender, subject, risk_score, expires_at, category
  FROM emails
  WHERE id = '$email_id';"

# Check ES value
curl "http://localhost:9200/emails/_doc/$email_id?pretty"

# Recompute for this email
python -c "
from app.db import SessionLocal
from app.models import Email
from scripts.analyze_risk import compute_risk_score

db = SessionLocal()
email = db.query(Email).filter_by(id='$email_id').first()
score, breakdown = compute_risk_score(email)
print(f'Computed score: {score}')
print(f'Breakdown: {breakdown}')
db.close()
"
```text

### 4. Category Classification Drift

**Symptoms:**

- Mismatches concentrated in `category` field
- DB vs ES show different categories

**Fix:**

```powershell
# Check category distribution in DB
docker-compose exec db psql -U postgres -d applylens -c "
  SELECT category, COUNT(*) as count
  FROM emails
  GROUP BY category
  ORDER BY count DESC;"

# Rerun classification (if logic changed)
# TODO: Add category backfill script
```text

---

## Reconciliation Strategy

### For Small Drift (<10 mismatches)

1. Identify affected email IDs from parity report
2. Manually trigger reindex for those IDs
3. Re-run parity check to confirm fix

### For Large Drift (>100 mismatches)

1. Run full backfill (analyze_risk.py --backfill)
2. Wait 10 minutes for propagation
3. Run parity check again
4. Escalate if mismatches persist

---

## Manual Reconciliation

```powershell
# Extract mismatch IDs from report
$mismatches = Get-Content parity.json | ConvertFrom-Json | Select-Object -ExpandProperty mismatches
$ids = $mismatches | Select-Object -ExpandProperty id

# Recompute risk scores for these IDs (example)
foreach ($id in $ids | Select-Object -First 10) {
    Write-Host "Recomputing $id..."
    # TODO: Add API endpoint to recompute single email
}
```text

---

## CI Integration Notes

### PR Workflow

- **Threshold:** Allow ≤3 mismatches on PRs
- **Action:** Warn in PR comment, don't fail build
- **Purpose:** Allow iterative fixes

### Main Branch

- **Threshold:** 0 mismatches required
- **Action:** Fail build if any mismatches
- **Purpose:** Prevent drift from entering production

### Viewing CI Results

```bash
# Check GitHub Actions artifacts
# Navigate to: https://github.com/leok974/ApplyLens/actions
# Download: parity.json, parity.csv from latest run
```text

---

## Monitoring Queries

### Grafana (PromQL)

```promql
# Current mismatch ratio
applylens_parity_mismatch_ratio

# Mismatch rate (per hour)
rate(applylens_parity_mismatches_total[1h])

# Time since last check
(time() - applylens_parity_last_check_timestamp) / 3600
```text

### Alert Thresholds

```yaml
# Alert if ratio > 0.5% for 15 minutes
expr: max_over_time(applylens_parity_mismatch_ratio[30m]) > 0.005
for: 15m

# Alert if check hasn't run in 24 hours
expr: (time() - applylens_parity_last_check_timestamp) > 86400
for: 5m
```text

---

## Post-Incident

1. **Analyze root cause:**
   - Was it a code bug?
   - ES replication lag?
   - Missing backfill after migration?

2. **Update tests:**
   - Add regression test if logic bug
   - Update parity thresholds if needed

3. **Document patterns:**
   - Update this runbook with new learnings
   - Share findings with team

---

## Useful Queries

### Database

```sql
-- Find records with NULL risk_score
SELECT COUNT(*) FROM emails WHERE risk_score IS NULL;

-- Find records updated recently
SELECT id, sender, risk_score, expires_at, category, updated_at
FROM emails
WHERE updated_at > NOW() - INTERVAL '1 hour'
ORDER BY updated_at DESC
LIMIT 20;
```text

### Elasticsearch

```bash
# Count documents
curl http://localhost:9200/emails/_count

# Check mapping
curl http://localhost:9200/emails/_mapping?pretty

# Sample documents
curl http://localhost:9200/emails/_search?pretty&size=5
```text

---

## Related Links

- [Parity Check Script](../../scripts/check_parity.py)
- [Parity Integration Tests](../../tests/integration/test_parity_job.py)
- [Phase 12.2 Documentation](../PHASE_12.2_PLAN.md)
- [CI Workflow](.github/workflows/automation-tests.yml)
