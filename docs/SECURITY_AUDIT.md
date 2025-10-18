# Security & Privacy Audit Template

**Version:** 1.0  
**Last Updated:** October 17, 2025  
**Audit Frequency:** Quarterly

---

## Audit Information

**Audit Period:** [Start Date] to [End Date]  
**Auditor:** [Name]  
**Date Completed:** [Date]  
**Next Audit Due:** [Date + 90 days]

---

## 1. PII Access Review

### 1.1 PII Audit Log Analysis

**Objective:** Review all PII access logs for unauthorized or suspicious access

```sql
-- Query: PII access in audit period
SELECT 
    timestamp,
    user_id,
    action,
    pii_type,
    resource_type,
    justification
FROM pii_audit_log
WHERE timestamp BETWEEN '[START_DATE]' AND '[END_DATE]'
ORDER BY timestamp DESC;
```

**Findings:**

| User ID | Action | PII Type | Resource | Justification | Authorized? |
|---------|--------|----------|----------|---------------|-------------|
| | | | | | ☐ Yes ☐ No |
| | | | | | ☐ Yes ☐ No |
| | | | | | ☐ Yes ☐ No |

**Unauthorized Access Incidents:** [Count]

**Actions Required:**
- [ ] Investigate unauthorized access
- [ ] Revoke access if needed
- [ ] Update access controls
- [ ] Notify security team

---

### 1.2 PII Detection Accuracy

**Objective:** Validate PII scanner is detecting and redacting correctly

**Test Cases:**

```bash
# Run PII scanner tests
cd services/api
pytest tests/test_privacy.py::TestPIIScanner -v
```

**Results:**

| Test | Status | Notes |
|------|--------|-------|
| Email detection | ☐ Pass ☐ Fail | |
| Phone detection | ☐ Pass ☐ Fail | |
| SSN detection | ☐ Pass ☐ Fail | |
| Credit card detection | ☐ Pass ☐ Fail | |
| API key detection | ☐ Pass ☐ Fail | |
| Redaction accuracy | ☐ Pass ☐ Fail | |

**Issues Found:** [List any false positives/negatives]

**Actions Required:**
- [ ] Update PII patterns if needed
- [ ] Retrain detection model
- [ ] Update test cases

---

### 1.3 Log Redaction Verification

**Objective:** Verify logs are properly redacted

```bash
# Sample recent logs
aws logs tail /aws/ecs/applylens-api --since 24h | head -100

# Check for PII patterns (should be [REDACTED])
grep -E "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" logs.txt
grep -E "\d{3}-\d{2}-\d{4}" logs.txt  # SSN pattern
grep -E "\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}" logs.txt  # Credit card
```

**Findings:**

- **Unredacted PII Found:** ☐ Yes ☐ No
- **PII Types Found:** [List if any]
- **Log Lines Affected:** [Count]

**Actions Required:**
- [ ] Update log redaction rules
- [ ] Purge logs with unredacted PII
- [ ] Verify redaction service is running

---

## 2. Consent Management

### 2.1 Active Consent Records

**Objective:** Review consent status and expiration

```sql
-- Query: Consent summary
SELECT 
    consent_type,
    status,
    COUNT(*) as count
FROM consent_records
WHERE created_at BETWEEN '[START_DATE]' AND '[END_DATE]'
GROUP BY consent_type, status
ORDER BY consent_type, status;
```

**Summary:**

| Consent Type | Granted | Denied | Withdrawn | Expired |
|--------------|---------|--------|-----------|---------|
| ESSENTIAL | | | | |
| ANALYTICS | | | | |
| MARKETING | | | | |
| PERSONALIZATION | | | | |
| THIRD_PARTY | | | | |

**Findings:**
- **Total Active Consents:** [Count]
- **Expired Consents:** [Count]
- **Withdrawal Rate:** [Percentage]

**Actions Required:**
- [ ] Contact users with expired consents
- [ ] Archive expired records
- [ ] Update consent UI if high withdrawal rate

---

### 2.2 Consent Version Tracking

**Objective:** Verify users are on latest consent version

```sql
-- Query: Consent versions
SELECT 
    version,
    COUNT(DISTINCT user_id) as user_count
FROM consent_records
WHERE status = 'GRANTED'
GROUP BY version
ORDER BY version DESC;
```

**Findings:**

| Version | User Count | % of Total | Current? |
|---------|------------|------------|----------|
| | | | ☐ Yes ☐ No |
| | | | ☐ Yes ☐ No |

**Actions Required:**
- [ ] Prompt users on old versions to re-consent
- [ ] Archive old consent versions
- [ ] Update consent text if needed

---

## 3. Data Subject Rights (DSR)

### 3.1 DSR Request Processing

**Objective:** Review DSR request handling and timeliness

```sql
-- Query: DSR requests in audit period
SELECT 
    request_id,
    user_id,
    right_type,
    status,
    requested_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - requested_at))/86400 as days_to_complete
FROM data_subject_requests
WHERE requested_at BETWEEN '[START_DATE]' AND '[END_DATE]'
ORDER BY requested_at DESC;
```

**Summary:**

| Right Type | Total | Completed | Pending | Overdue |
|------------|-------|-----------|---------|---------|
| ACCESS | | | | |
| RECTIFICATION | | | | |
| ERASURE | | | | |
| RESTRICT | | | | |
| PORTABILITY | | | | |
| OBJECT | | | | |

**Performance Metrics:**
- **Average Response Time:** [Days]
- **GDPR Compliance (30-day deadline):** [Percentage]
- **Overdue Requests:** [Count]

**Findings:**
- [ ] ☐ All requests processed within 30 days
- [ ] ☐ Overdue requests identified
- [ ] ☐ Response time trending

**Actions Required:**
- [ ] Prioritize overdue requests
- [ ] Improve process if avg >30 days
- [ ] Update automation workflows

---

### 3.2 Data Export Quality

**Objective:** Validate data exports are complete and accurate

**Sample Test:**

```bash
# Generate test data export
curl -X POST https://api.applylens.io/security/dsr/request \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-123",
    "user_email": "test@example.com",
    "right_type": "ACCESS"
  }'

# Download and verify export
# Check: All user data tables included
# Check: Data is readable JSON format
# Check: PII is NOT redacted (it's their data)
```

**Findings:**

- **Export Format:** ☐ JSON ☐ CSV ☐ Other
- **Data Completeness:** ☐ Complete ☐ Incomplete
- **Data Tables Included:** [Count]
- **Issues Found:** [List]

**Actions Required:**
- [ ] Add missing data tables to export
- [ ] Fix format issues
- [ ] Update export template

---

## 4. Data Retention

### 4.1 Retention Policy Compliance

**Objective:** Verify data is deleted per retention policies

```sql
-- Query: Data eligible for deletion
SELECT 
    data_type,
    retention_days,
    legal_basis,
    COUNT(*) as records_eligible
FROM (
    SELECT 
        'user_profile' as data_type,
        7 * 365 as retention_days,
        'Contract necessity' as legal_basis,
        COUNT(*) OVER()
    FROM users
    WHERE deleted_at IS NULL
    AND last_login < NOW() - INTERVAL '7 years'
    
    UNION ALL
    
    SELECT 
        'email' as data_type,
        365 as retention_days,
        'Contract necessity' as legal_basis,
        COUNT(*) OVER()
    FROM emails
    WHERE created_at < NOW() - INTERVAL '1 year'
    
    UNION ALL
    
    SELECT 
        'analytics' as data_type,
        90 as retention_days,
        'Legitimate interest' as legal_basis,
        COUNT(*) OVER()
    FROM analytics_events
    WHERE event_date < NOW() - INTERVAL '90 days'
) as retention_check
GROUP BY data_type, retention_days, legal_basis;
```

**Findings:**

| Data Type | Retention Period | Records Eligible | Deleted? |
|-----------|------------------|------------------|----------|
| user_profile | 7 years | | ☐ Yes ☐ No |
| email | 1 year | | ☐ Yes ☐ No |
| analytics | 90 days | | ☐ Yes ☐ No |
| audit | 7 years | | ☐ Yes ☐ No |
| marketing | 2 years | | ☐ Yes ☐ No |

**Actions Required:**
- [ ] Execute deletion for eligible records
- [ ] Verify deletion completed
- [ ] Archive deleted record IDs
- [ ] Update retention automation

---

### 4.2 Backup Retention

**Objective:** Ensure backups also respect retention policies

```bash
# Check database snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier applylens-prod \
  --region us-east-1 \
  --query 'DBSnapshots[?SnapshotCreateTime<`2024-10-17`]'

# Check S3 backup retention
aws s3api list-object-versions \
  --bucket applylens-backups \
  --prefix database/ \
  --query 'Versions[?LastModified<`2024-10-17`]'
```

**Findings:**

- **Snapshots >30 days:** [Count]
- **S3 backups >30 days:** [Count]
- **Lifecycle Policy Active:** ☐ Yes ☐ No

**Actions Required:**
- [ ] Delete old snapshots
- [ ] Update S3 lifecycle policy
- [ ] Verify automated cleanup

---

## 5. Access Control

### 5.1 User Access Review

**Objective:** Review who has access to production systems

**Production Access List:**

| User | Role | Systems | Last Access | Authorized? |
|------|------|---------|-------------|-------------|
| | Admin | AWS, DB, Deploy | | ☐ Yes ☐ No |
| | Engineer | DB, Logs | | ☐ Yes ☐ No |
| | SRE | AWS, DB, Deploy, Logs | | ☐ Yes ☐ No |

**Findings:**
- **Total Users with Prod Access:** [Count]
- **Inactive Accounts (>90 days):** [Count]
- **Overprivileged Accounts:** [Count]

**Actions Required:**
- [ ] Revoke access for inactive accounts
- [ ] Reduce privileges for overprivileged accounts
- [ ] Update access control policies
- [ ] Enable MFA for all admin accounts

---

### 5.2 API Key Rotation

**Objective:** Ensure API keys are rotated regularly

```bash
# List API keys and last rotation date
aws iam list-access-keys --user-name applylens-prod
aws iam get-access-key-last-used --access-key-id <KEY_ID>
```

**Findings:**

| Service | Key Age | Rotation Required? | Rotated? |
|---------|---------|--------------------| ---------|
| Gmail API | | ☐ Yes (>90 days) ☐ No | ☐ Yes ☐ No |
| Elasticsearch | | ☐ Yes (>90 days) ☐ No | ☐ Yes ☐ No |
| AWS IAM | | ☐ Yes (>90 days) ☐ No | ☐ Yes ☐ No |
| PagerDuty | | ☐ Yes (>90 days) ☐ No | ☐ Yes ☐ No |

**Actions Required:**
- [ ] Rotate keys >90 days old
- [ ] Update key rotation schedule
- [ ] Enable automated rotation

---

## 6. Vulnerability Scanning

### 6.1 Dependency Vulnerabilities

**Objective:** Scan for known vulnerabilities in dependencies

```bash
# Python dependencies
cd services/api
pip-audit

# JavaScript dependencies
cd web
npm audit

# Docker images
docker scan applylens/api:latest
```

**Findings:**

| Package | Vulnerability | Severity | Fixed Version | Patched? |
|---------|---------------|----------|---------------|----------|
| | | ☐ Critical ☐ High ☐ Medium ☐ Low | | ☐ Yes ☐ No |
| | | ☐ Critical ☐ High ☐ Medium ☐ Low | | ☐ Yes ☐ No |

**Summary:**
- **Critical:** [Count]
- **High:** [Count]
- **Medium:** [Count]
- **Low:** [Count]

**Actions Required:**
- [ ] Patch critical and high vulnerabilities immediately
- [ ] Schedule medium/low for next sprint
- [ ] Update dependencies
- [ ] Rerun scan to verify

---

### 6.2 Infrastructure Security

**Objective:** Review AWS security posture

```bash
# Run AWS Security Hub
aws securityhub get-findings \
  --filters '{"SeverityLabel":[{"Value":"CRITICAL","Comparison":"EQUALS"}]}' \
  --region us-east-1

# Check for public S3 buckets
aws s3api list-buckets --query 'Buckets[*].Name' | \
  xargs -I {} aws s3api get-bucket-acl --bucket {}

# Check for open security groups
aws ec2 describe-security-groups \
  --filters "Name=ip-permission.cidr,Values=0.0.0.0/0" \
  --region us-east-1
```

**Findings:**

| Finding | Severity | Status | Remediated? |
|---------|----------|--------|-------------|
| | ☐ Critical ☐ High ☐ Medium ☐ Low | | ☐ Yes ☐ No |
| | ☐ Critical ☐ High ☐ Medium ☐ Low | | ☐ Yes ☐ No |

**Actions Required:**
- [ ] Fix critical/high findings
- [ ] Update security group rules
- [ ] Enable GuardDuty if not active
- [ ] Review IAM policies

---

## 7. Compliance Checklist

### 7.1 GDPR Compliance

**Article 5: Principles**
- [ ] Lawfulness, fairness, transparency (consent tracking)
- [ ] Purpose limitation (data used only for stated purpose)
- [ ] Data minimization (only collect necessary data)
- [ ] Accuracy (rectification process in place)
- [ ] Storage limitation (retention policies enforced)
- [ ] Integrity and confidentiality (encryption at rest/transit)

**Article 15-21: Data Subject Rights**
- [ ] Right to access (export functionality)
- [ ] Right to rectification (user can update data)
- [ ] Right to erasure (deletion process)
- [ ] Right to restrict processing (consent withdrawal)
- [ ] Right to data portability (JSON export)
- [ ] Right to object (opt-out available)

**Article 33-34: Breach Notification**
- [ ] 72-hour breach notification process documented
- [ ] DPO or contact designated
- [ ] Breach response plan in place

---

### 7.2 CCPA Compliance

**Consumer Rights**
- [ ] Right to know what data is collected
- [ ] Right to delete data
- [ ] Right to opt-out of sale (not applicable - we don't sell)
- [ ] Right to non-discrimination

**Business Requirements**
- [ ] Privacy policy updated within 12 months
- [ ] "Do Not Sell My Personal Information" link (if applicable)
- [ ] Designated methods for submitting requests
- [ ] Response within 45 days

---

## 8. Audit Summary

### Overall Compliance Score

| Area | Score | Status |
|------|-------|--------|
| PII Access Review | [X]/10 | ☐ Pass ☐ Needs Improvement ☐ Fail |
| Consent Management | [X]/10 | ☐ Pass ☐ Needs Improvement ☐ Fail |
| DSR Processing | [X]/10 | ☐ Pass ☐ Needs Improvement ☐ Fail |
| Data Retention | [X]/10 | ☐ Pass ☐ Needs Improvement ☐ Fail |
| Access Control | [X]/10 | ☐ Pass ☐ Needs Improvement ☐ Fail |
| Vulnerability Management | [X]/10 | ☐ Pass ☐ Needs Improvement ☐ Fail |
| GDPR Compliance | [X]/10 | ☐ Pass ☐ Needs Improvement ☐ Fail |
| CCPA Compliance | [X]/10 | ☐ Pass ☐ Needs Improvement ☐ Fail |

**Overall Score:** [Total]/80  
**Overall Status:** ☐ Pass (≥64) ☐ Needs Improvement (48-63) ☐ Fail (<48)

---

### Critical Findings

1. **[Severity]** [Description]
   - Impact: [User/Business impact]
   - Action: [Required action]
   - Owner: [Assigned to]
   - Deadline: [Date]

2. **[Severity]** [Description]
   - Impact: [User/Business impact]
   - Action: [Required action]
   - Owner: [Assigned to]
   - Deadline: [Date]

---

### Action Items

| Priority | Action | Owner | Deadline | Status |
|----------|--------|-------|----------|--------|
| P0 | | | | ☐ Not Started ☐ In Progress ☐ Complete |
| P1 | | | | ☐ Not Started ☐ In Progress ☐ Complete |
| P2 | | | | ☐ Not Started ☐ In Progress ☐ Complete |

---

## Signatures

**Auditor:**  
Name: ___________________________  
Signature: ___________________________  
Date: ___________________________

**Engineering Manager:**  
Name: ___________________________  
Signature: ___________________________  
Date: ___________________________

**DPO/Compliance Officer:**  
Name: ___________________________  
Signature: ___________________________  
Date: ___________________________

---

**Next Audit Due:** [Date + 90 days]  
**Audit Report Filed:** ☐ Yes ☐ No  
**Audit Report Location:** `s3://applylens-compliance/audits/security-[DATE].pdf`
