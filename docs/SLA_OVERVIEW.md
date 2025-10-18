# ApplyLens Service Level Agreements (SLA)

**Version:** 1.0  
**Last Updated:** October 17, 2025  
**Effective Date:** January 1, 2025

## Overview

This document defines the Service Level Agreements (SLAs) for ApplyLens platform services. SLAs represent our commitments to customers, while Service Level Objectives (SLOs) are internal targets we use to maintain service quality.

### Key Definitions

- **SLO (Service Level Objective):** Internal target we aim to meet (e.g., 99.5% uptime)
- **SLA (Service Level Agreement):** Customer-facing commitment (e.g., 99% uptime guarantee)
- **Error Budget:** Allowed failure rate = 100% - SLO (e.g., 0.5% for 99.5% SLO)
- **SLI (Service Level Indicator):** Quantitative measure (e.g., request success rate)

### SLO vs SLA Buffer

We maintain a **0.4% buffer** between internal SLO targets and customer-facing SLA commitments. This buffer allows us to detect and fix issues before impacting customer guarantees.

Example:
- **Internal SLO:** 99.5% success rate
- **Customer SLA:** 99.0% success rate
- **Buffer:** 0.5% for operational flexibility

---

## Platform-Wide SLA

### Uptime Guarantee

**SLA:** 99.0% uptime per calendar month

- **Downtime Budget:** 43.2 minutes/month (30 days × 24 hours × 0.01)
- **Measurement:** Based on API health endpoint availability
- **Exclusions:** Scheduled maintenance (with 7-day notice)

### Availability Calculation

```
Uptime % = (Total Minutes - Downtime Minutes) / Total Minutes × 100
```

**Example:**
- Total minutes in January: 44,640 (31 days)
- Downtime: 30 minutes
- Uptime: (44,640 - 30) / 44,640 × 100 = 99.93%
- **Result:** ✅ SLA met (>99.0%)

### SLA Credits

If we fail to meet the 99.0% uptime SLA:

| Uptime % | Service Credit |
|----------|----------------|
| 99.0% - 98.0% | 10% monthly fee |
| 98.0% - 95.0% | 25% monthly fee |
| <95.0% | 50% monthly fee |

**Claim Process:** Email support@applylens.io within 30 days

---

## Agent-Level SLAs

### 1. inbox.triage (Email Classification)

**Purpose:** Classify and prioritize incoming emails

#### Performance SLAs

| Metric | SLO Target | SLA Guarantee | Measurement |
|--------|------------|---------------|-------------|
| Latency (P95) | <1.5 seconds | <2.0 seconds | 95th percentile response time |
| Success Rate | >98% | >95% | Successful classifications / total requests |
| Precision | >95% | >90% | Correctly classified / total classified |
| Freshness | <30 minutes | <60 minutes | Time since last email processed |

#### Error Budget

- **Monthly Request Budget:** 500,000 requests
- **Allowed Failures (SLO):** 10,000 failures (2% error rate)
- **Allowed Failures (SLA):** 25,000 failures (5% error rate)

#### Cost Commitment

- **Target Cost:** <$0.05 per request
- **Maximum Cost:** <$0.10 per request

---

### 2. inbox.search (Email Search)

**Purpose:** Semantic search across email corpus

#### Performance SLAs

| Metric | SLO Target | SLA Guarantee | Measurement |
|--------|------------|---------------|-------------|
| Latency (P95) | <800ms | <1.2 seconds | 95th percentile response time |
| Success Rate | >99% | >97% | Successful searches / total requests |
| Recall | >95% | >90% | Relevant results found / total relevant |
| Index Lag | <5 minutes | <15 minutes | Indexing delay for new emails |

#### Error Budget

- **Monthly Request Budget:** 1,000,000 requests
- **Allowed Failures (SLO):** 10,000 failures (1% error rate)
- **Allowed Failures (SLA):** 30,000 failures (3% error rate)

#### Cost Commitment

- **Target Cost:** <$0.02 per request
- **Maximum Cost:** <$0.05 per request

---

### 3. knowledge.search (Knowledge Graph)

**Purpose:** Query company knowledge base

#### Performance SLAs

| Metric | SLO Target | SLA Guarantee | Measurement |
|--------|------------|---------------|-------------|
| Latency (P95) | <1.0 second | <1.5 seconds | 95th percentile response time |
| Success Rate | >98% | >95% | Successful queries / total requests |
| Relevance | >90% | >85% | Relevant results in top 10 |
| Freshness | Real-time | <5 minutes | Knowledge update lag |

#### Error Budget

- **Monthly Request Budget:** 200,000 requests
- **Allowed Failures (SLO):** 4,000 failures (2% error rate)
- **Allowed Failures (SLA):** 10,000 failures (5% error rate)

#### Cost Commitment

- **Target Cost:** <$0.03 per request
- **Maximum Cost:** <$0.08 per request

---

### 4. planner.deploy (Deployment Planning)

**Purpose:** Generate and validate deployment plans

#### Performance SLAs

| Metric | SLO Target | SLA Guarantee | Measurement |
|--------|------------|---------------|-------------|
| Latency (P95) | <5.0 seconds | <8.0 seconds | 95th percentile response time |
| Success Rate | >95% | >90% | Valid plans generated / total requests |
| Accuracy | >90% | >85% | Plans without errors |

#### Error Budget

- **Monthly Request Budget:** 50,000 requests
- **Allowed Failures (SLO):** 2,500 failures (5% error rate)
- **Allowed Failures (SLA):** 5,000 failures (10% error rate)

#### Cost Commitment

- **Target Cost:** <$0.20 per request
- **Maximum Cost:** <$0.40 per request

---

### 5. warehouse.health (Data Quality)

**Purpose:** Monitor data warehouse health

#### Performance SLAs

| Metric | SLO Target | SLA Guarantee | Measurement |
|--------|------------|---------------|-------------|
| Latency (P95) | <2.0 seconds | <3.0 seconds | 95th percentile response time |
| Success Rate | >98% | >95% | Successful checks / total requests |
| Freshness | <60 minutes | <120 minutes | Data staleness threshold |
| Quality Score | >95% | >90% | Passed checks / total checks |

#### Error Budget

- **Monthly Request Budget:** 100,000 requests
- **Allowed Failures (SLO):** 2,000 failures (2% error rate)
- **Allowed Failures (SLA):** 5,000 failures (5% error rate)

#### Cost Commitment

- **Target Cost:** <$0.10 per request
- **Maximum Cost:** <$0.20 per request

---

### 6. analytics.insights (Business Intelligence)

**Purpose:** Generate business insights from data

#### Performance SLAs

| Metric | SLO Target | SLA Guarantee | Measurement |
|--------|------------|---------------|-------------|
| Latency (P95) | <3.0 seconds | <5.0 seconds | 95th percentile response time |
| Success Rate | >97% | >92% | Successful insights / total requests |
| Data Accuracy | >95% | >90% | Verified insights / total insights |

#### Error Budget

- **Monthly Request Budget:** 150,000 requests
- **Allowed Failures (SLO):** 4,500 failures (3% error rate)
- **Allowed Failures (SLA):** 12,000 failures (8% error rate)

#### Cost Commitment

- **Target Cost:** <$0.15 per request
- **Maximum Cost:** <$0.30 per request

---

## Monitoring & Alerts

### Error Budget Tracking

We track error budget consumption in real-time:

**Fast Burn Alert (Critical):**
- Consuming >14.4x normal rate (1-hour window)
- Will exhaust budget in <2 hours
- **Action:** Page on-call immediately

**Slow Burn Alert (Warning):**
- Consuming >6x normal rate (6-hour window)
- Will exhaust budget in <5 days
- **Action:** Notify on-call via Slack

### Dashboards

- **SLO Compliance:** https://grafana.applylens.io/d/slo-compliance
- **Error Budget:** https://grafana.applylens.io/d/error-budget
- **Agent Performance:** https://grafana.applylens.io/d/agent-performance

### Prometheus Queries

```promql
# SLO compliance (4-week rolling window)
sum(rate(applylens_agent_success_total{agent="inbox.triage"}[4w]))
/
sum(rate(applylens_agent_requests_total{agent="inbox.triage"}[4w]))

# Error budget remaining
1 - (
  sum(rate(applylens_agent_errors_total{agent="inbox.triage"}[4w]))
  /
  sum(rate(applylens_agent_requests_total{agent="inbox.triage"}[4w]))
) / (1 - 0.98)  # 0.98 = SLO target

# Burn rate (last 1 hour)
sum(rate(applylens_agent_errors_total{agent="inbox.triage"}[1h]))
/
sum(rate(applylens_agent_requests_total{agent="inbox.triage"}[1h]))
```

---

## Maintenance Windows

### Scheduled Maintenance

- **Frequency:** Monthly (first Saturday of each month)
- **Duration:** 2 hours (02:00-04:00 UTC)
- **Notice:** 7 days advance notification
- **Scope:** Database upgrades, infrastructure patches

### Emergency Maintenance

- **Notice:** Best effort (may be immediate)
- **Scope:** Critical security patches, urgent bug fixes
- **Duration:** Variable (typically <1 hour)

**Note:** Scheduled maintenance is excluded from uptime SLA calculations.

---

## Incident Response Commitments

### Response Times

| Severity | SLA Response Time | SLA Resolution Time |
|----------|-------------------|---------------------|
| SEV1 (Outage) | <5 minutes | <2 hours |
| SEV2 (Degradation) | <15 minutes | <4 hours |
| SEV3 (Minor Issue) | <2 hours | <24 hours |
| SEV4 (Low Priority) | <1 business day | <5 business days |

### Communication

- **Status Page:** https://status.applylens.io
- **Email Notifications:** Sent to account admin
- **Slack Updates:** Every 15 minutes during active incidents

---

## Data Protection SLA

### Backup & Recovery

| Metric | SLA Guarantee |
|--------|---------------|
| Backup Frequency | Daily (automated) |
| Backup Retention | 30 days |
| Recovery Time Objective (RTO) | <4 hours |
| Recovery Point Objective (RPO) | <24 hours |

### Data Durability

- **Guarantee:** 99.999999999% (11 nines)
- **Implementation:** AWS S3 with cross-region replication

---

## Support SLA

### Support Channels

| Channel | Response Time | Business Hours |
|---------|---------------|----------------|
| Email (support@applylens.io) | <4 hours | 9am-5pm ET, Mon-Fri |
| Slack (Enterprise) | <1 hour | 9am-5pm ET, Mon-Fri |
| Phone (Critical Issues) | <15 minutes | 24/7 |

### Support Tiers

**Standard Support:**
- Email support during business hours
- Response time: <4 hours

**Premium Support:**
- 24/7 phone support
- Response time: <15 minutes
- Dedicated success manager

---

## SLA Review Process

### Monthly Review

On the 1st of each month, we publish:
1. SLA compliance report
2. Incident summary
3. Performance trends
4. Upcoming improvements

### Continuous Improvement

Based on SLA performance, we:
- Adjust SLO targets if consistently exceeded
- Investigate if error budget exhausted
- Update runbooks for recurring issues
- Invest in automation to reduce MTTR

---

## Contact Information

### SLA Questions
- Email: sla@applylens.io
- Documentation: https://docs.applylens.io/sla

### Incident Reports
- Email: incidents@applylens.io
- Status Page: https://status.applylens.io

### Service Credits
- Email: billing@applylens.io
- Claim within 30 days of incident

---

**Document Ownership:** SRE Team  
**Review Frequency:** Quarterly  
**Last Review:** October 17, 2025  
**Next Review:** January 17, 2026
