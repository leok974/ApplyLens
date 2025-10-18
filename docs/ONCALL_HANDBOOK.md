# On-Call Handbook

**Version:** 1.0  
**Last Updated:** October 17, 2025  
**Audience:** On-Call Engineers

## Welcome to On-Call!

This handbook guides you through your on-call shift, from preparation to handoff. On-call at ApplyLens typically involves 1-3 incidents per week, with most resolved within 30 minutes.

---

## On-Call Schedule

### Rotation Details

- **Primary On-Call:** 1-week rotation (Monday 9am → Monday 9am)
- **Secondary On-Call:** Backup for escalation (15-minute delay)
- **Manager On-Call:** Escalation for SEV1 after 30 minutes
- **Schedule Tool:** PagerDuty (https://applylens.pagerduty.com/)

### Current Rotation

Check PagerDuty for current schedule:

```bash
# Via PagerDuty CLI (if installed)
pd-oncall who

# Or visit: https://applylens.pagerduty.com/schedules
```

### Time Commitment

**Expected Load:**
- **Weekday (9am-5pm):** 2-4 alerts/day (mostly SEV3/SEV4)
- **Weekday (after hours):** 0-1 alert/night (rarely critical)
- **Weekend:** 0-2 alerts/weekend (usually automated)

**MTTR (Mean Time to Resolve):**
- SEV1: 15-60 minutes
- SEV2: 30-120 minutes
- SEV3: 1-4 hours
- SEV4: 1-3 days

---

## Pre-Shift Checklist

### 24 Hours Before

- [ ] Review PagerDuty schedule confirmation
- [ ] Check for known issues or upcoming deployments
- [ ] Review recent incidents (past week)
- [ ] Test PagerDuty notifications (mobile app + SMS)
- [ ] Ensure laptop is charged and accessible
- [ ] Review this handbook

### Start of Shift

- [ ] Acknowledge shift start in `#on-call` Slack channel
- [ ] Review current system status (dashboards)
- [ ] Check for any ongoing issues from previous shift
- [ ] Read handoff notes from previous on-call
- [ ] Verify access to critical systems:
  - [ ] AWS Console
  - [ ] Database (psql)
  - [ ] Deployment scripts
  - [ ] Grafana dashboards
  - [ ] PagerDuty

**Handoff Message Template:**

```
👋 **On-Call Shift Starting**

**Engineer:** @your-name
**Dates:** Oct 17 - Oct 24, 9am ET
**Backup:** @secondary-oncall

**Current Status:**
✅ All systems healthy
✅ No ongoing incidents
✅ Next deployment: Oct 20 (staging)

**Notes from previous shift:**
- Slow burn alert on analytics.insights (resolved)
- Database maintenance scheduled for Oct 19, 2am UTC

Ready for alerts! 🚨
```

---

## Alert Response

### Response Times by Severity

| Severity | Acknowledge | Initial Response | Resolution Target |
|----------|-------------|------------------|-------------------|
| SEV1 | <2 min | <5 min | <2 hours |
| SEV2 | <5 min | <15 min | <4 hours |
| SEV3 | <30 min | <2 hours | <24 hours |
| SEV4 | <4 hours | <1 business day | <5 business days |

### Alert Acknowledgment

**Via PagerDuty Mobile App:**
1. Receive push notification
2. Open incident
3. Tap "Acknowledge"
4. Add quick note: "Investigating"

**Via Phone:**
1. Receive phone call
2. Press 4 to acknowledge
3. Incident stops calling

**Via CLI:**

```bash
# Acknowledge incident
pd-incident ack <incident-id>
```

**IMPORTANT:** Always acknowledge within response time, even if you can't immediately resolve.

---

## Incident Management

### Step 1: Assess Severity

```bash
# Check alert details in PagerDuty
# Determine severity based on:
# - Number of affected users
# - Service availability
# - Data integrity risk
# - Business impact

# SEV1: Complete outage, all users affected
# SEV2: Significant degradation, >10% users affected
# SEV3: Minor issues, <10% users affected
# SEV4: Low priority, no immediate user impact
```

### Step 2: Create Incident Channel (SEV1/SEV2)

```bash
# Slack incident channel auto-created by PagerDuty
# Channel name: #incident-{timestamp}

# Post initial status
🚨 **SEV1/SEV2: [Brief Description]**
**Started:** [Time] UTC
**Status:** Investigating
**IC:** @your-name
**Impact:** [User-facing impact]

Updates every 5-15 minutes depending on severity.
```

### Step 3: Investigate

Follow the appropriate playbook:

- **API Outage:** [PLAYBOOK_API_OUTAGE.md](playbooks/PLAYBOOK_API_OUTAGE.md)
- **SLO Violation:** [PLAYBOOK_SLO_VIOLATION.md](playbooks/PLAYBOOK_SLO_VIOLATION.md)
- **Database Issues:** [PLAYBOOK_DATABASE_ISSUES.md](playbooks/PLAYBOOK_DATABASE_ISSUES.md)

### Step 4: Escalate if Needed

**Escalation Triggers:**
- Unable to identify root cause within 15 minutes (SEV1)
- Resolution requires expertise you don't have
- Incident duration exceeds MTTR target
- Multiple services affected simultaneously

**Escalation Path:**
1. **Secondary On-Call** (automatic after 15 min if not acknowledged)
2. **Engineering Manager** (page via PagerDuty after 30 min for SEV1)
3. **VP Engineering** (page via PagerDuty after 1 hour for SEV1)

**How to Escalate:**

```bash
# Via PagerDuty
# 1. Open incident
# 2. Click "Escalate"
# 3. Select escalation policy
# 4. Add context note

# Via Slack
@secondary-oncall Need help with SEV1 - API outage
Root cause unclear after 15 min investigation
```

### Step 5: Communicate Status

**Update Frequency:**
- **SEV1:** Every 5 minutes
- **SEV2:** Every 15 minutes
- **SEV3:** Every 1-2 hours
- **SEV4:** Daily

**Update Template:**

```
🔄 **UPDATE [15:45 UTC]**
**Status:** [Investigating / Identified / Resolving / Monitoring]
**Action:** [Current action being taken]
**Progress:** [Metrics showing improvement/degradation]
**ETA:** [Estimated resolution time]
```

### Step 6: Resolve and Verify

```bash
# After fix applied, verify:

# 1. Health checks pass
curl https://api.applylens.io/health

# 2. Metrics return to normal
open https://grafana.applylens.io/d/system-health

# 3. Alerts cleared
# Check PagerDuty - incident should auto-resolve

# 4. User validation
# Test critical user flows
```

### Step 7: Document and Close

```bash
# Post resolution message
✅ **INCIDENT RESOLVED [16:10 UTC]**
**Duration:** [X minutes]
**Cause:** [Brief root cause]
**Resolution:** [What fixed it]
**Impact:** [User impact summary]

Monitoring for 30 minutes. Will schedule postmortem.

# Resolve PagerDuty incident
# Add resolution notes to incident

# Create postmortem ticket (SEV1/SEV2 only)
# Template: docs/templates/POSTMORTEM.md
```

---

## Common Alerts

### Fast Burn Rate Alert (SEV2)

**What it means:** Error budget burning too quickly

**Typical causes:**
- Recent deployment regression
- External service degradation
- Database performance issues

**First actions:**
1. Check recent deployments (last 2 hours)
2. Review error logs for patterns
3. Consider rollback if deployment-related

**Playbook:** [PLAYBOOK_SLO_VIOLATION.md](playbooks/PLAYBOOK_SLO_VIOLATION.md)

---

### Database Connection Pool Alert (SEV2)

**What it means:** Running out of database connections

**Typical causes:**
- Connection leaks in code
- Sudden traffic spike
- Long-running queries

**First actions:**
1. Check active connections: `SELECT count(*) FROM pg_stat_activity WHERE state = 'active';`
2. Kill idle connections: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction';`
3. Restart API pods if needed

**Playbook:** [PLAYBOOK_DATABASE_ISSUES.md](playbooks/PLAYBOOK_DATABASE_ISSUES.md)

---

### Elasticsearch Cluster Red (SEV1)

**What it means:** ES cluster unavailable or data loss risk

**Typical causes:**
- Node failure
- Disk space exhaustion
- Network partition

**First actions:**
1. Check cluster health: `curl es.applylens.io:9200/_cluster/health`
2. Check disk space: `curl es.applylens.io:9200/_cat/allocation?v`
3. Review ES logs for errors

**Playbook:** [PLAYBOOK_ELASTICSEARCH.md](playbooks/PLAYBOOK_ELASTICSEARCH.md)

---

### High Cost Alert (SEV3)

**What it means:** Agent cost per request exceeds threshold

**Typical causes:**
- Model upgrade (GPT-3.5 → GPT-4)
- Increased token usage
- Request volume spike

**First actions:**
1. Check cost metrics dashboard
2. Identify which agent is expensive
3. Review recent config changes
4. Consider switching to smaller model for non-critical tasks

**Playbook:** [PLAYBOOK_COST_OPTIMIZATION.md](playbooks/PLAYBOOK_COST_OPTIMIZATION.md)

---

## Daily Operational Tasks

### Morning Check (9am ET)

```bash
# 1. Review overnight alerts
open https://applylens.pagerduty.com/incidents

# 2. Check SLO compliance
open https://grafana.applylens.io/d/slo-compliance

# 3. Review error budget status
curl -s http://api.applylens.io/metrics | grep error_budget_remaining

# 4. Check data quality reports
cd analytics/dbt
dbt test --select source:*

# 5. Review scheduled maintenance
# Check calendar for upcoming deployments

# 6. Post daily status in #sre channel
```

**Daily Status Template:**

```
☀️ **Daily On-Call Status - Oct 17**

**System Health:** ✅ All systems operational
**Error Budgets:** ✅ All agents >70%
**Overnight Incidents:** 1 slow burn (resolved)
**Today's Deployments:** None scheduled
**On-Call:** @your-name (primary), @backup-name (secondary)

Have a great day! ☕
```

### Afternoon Check (3pm ET)

```bash
# 1. Review afternoon metrics
# 2. Check for any slow trends
# 3. Verify backup completion (if daily backup time)
# 4. Update any ongoing incidents
```

### End-of-Day Check (5pm ET)

```bash
# 1. Review day's incidents
# 2. Update any handoff notes
# 3. Check for scheduled overnight maintenance
# 4. Ensure phone volume is on for overnight alerts
```

---

## Handoff Procedures

### End of Shift (Weekly Handoff)

- [ ] Write handoff notes in `#on-call` channel
- [ ] Document any ongoing issues
- [ ] List upcoming deployments/maintenance
- [ ] Note any system quirks or recent changes
- [ ] Transfer any open tickets to next on-call
- [ ] Schedule 15-minute handoff call (if needed)

**Handoff Message Template:**

```
👋 **On-Call Shift Ending**

**Outgoing:** @current-oncall
**Incoming:** @next-oncall
**Period:** Oct 17-24

**Shift Summary:**
- Total incidents: 4 (2 SEV3, 2 SEV4)
- Notable issues: Slow burn on analytics.insights (Oct 19, resolved)
- Deployments: Staging deploy on Oct 20 (successful)

**Ongoing Issues:**
- None

**Upcoming Events:**
- Database maintenance: Oct 26, 2am UTC
- Next prod deploy: Oct 27
- Holiday next week (reduced team)

**System Notes:**
- analytics.insights burn rate trending up, watch closely
- Added new index on emails table (Oct 22)
- External API (Gmail) had brief outage Oct 21

**Handoff Call:** Optional, ping me if questions

Good luck! 🎉
```

---

## Tools and Access

### Essential Tools

| Tool | Purpose | Access |
|------|---------|--------|
| PagerDuty | Incident management | https://applylens.pagerduty.com/ |
| Grafana | Metrics dashboards | https://grafana.applylens.io/ |
| AWS Console | Infrastructure | https://console.aws.amazon.com/ |
| Slack | Communication | #incidents, #sre, #alerts |
| GitHub | Code and deployments | https://github.com/leok974/ApplyLens |

### Access Verification

```bash
# Test AWS access
aws sts get-caller-identity

# Test database access
psql -h db.applylens.io -U applylens -d applylens -c "SELECT 1;"

# Test deployment script access
cd /opt/applylens/deploy/scripts
ls -l promote_release.py

# Test PagerDuty API
curl -H "Authorization: Token token=$PAGERDUTY_TOKEN" \
  https://api.pagerduty.com/users/me
```

### Getting Access

If you don't have access to any tool:
1. Post in `#sre` channel
2. Tag `@sre-lead`
3. Request access with justification
4. Access typically granted within 1 business day

**Emergency Access:** Call engineering manager directly

---

## Self-Care

### During Business Hours (9am-5pm ET)

- ✅ Respond to all alerts promptly
- ✅ Attend scheduled meetings (on-call takes priority if conflict)
- ✅ Take normal lunch break (notify secondary on-call)
- ✅ Continue regular work between incidents

### After Hours (Evenings, Nights, Weekends)

- ✅ Keep phone volume on and nearby
- ✅ Respond within response time SLAs
- ⚠️ You're not expected to work continuously after hours
- ⚠️ Only respond to pages, don't actively monitor
- ✅ Laptop within 5-10 minutes reach

### If You're Overwhelmed

**It's okay to ask for help!**

- Escalate to secondary on-call anytime
- Reach out in `#sre` channel for advice
- Call engineering manager if multiple SEV1s
- Request additional help if needed

**Remember:** Your wellbeing matters. Incidents will happen, that's why we have teams.

---

## Escalation Contacts

### Primary Escalation (Always Available)

- **Secondary On-Call:** PagerDuty auto-escalates after 15 min
- **Engineering Manager:** Page via PagerDuty for SEV1 >30 min

### Subject Matter Experts

| Area | Expert | Contact |
|------|--------|---------|
| Database | @db-expert | Slack or PagerDuty |
| Elasticsearch | @es-expert | Slack or PagerDuty |
| ML Models | @ml-expert | Slack (business hours) |
| Billing | @billing-expert | Slack (business hours) |
| Security | @security-expert | PagerDuty (24/7) |

### External Vendor Support

| Vendor | Contact | Use For |
|--------|---------|---------|
| AWS | AWS Support Portal | Infrastructure issues |
| Elastic Cloud | support@elastic.co | ES cluster issues |
| PagerDuty | support@pagerduty.com | PagerDuty platform issues |

---

## FAQs

### Q: What if I'm traveling during my shift?

**A:** Inform team 1 week in advance. Ensure:
- Stable internet access
- Laptop and charger
- Phone with PagerDuty app
- Time zone adjustments communicated

### Q: What if I'm sick during my shift?

**A:** Post in `#sre` immediately. Engineering manager will arrange coverage. Your health comes first.

### Q: Can I swap shifts?

**A:** Yes! Coordinate with another engineer:
1. Get their agreement
2. Update PagerDuty schedule
3. Post in `#on-call` channel
4. Get manager approval

### Q: What if alert wakes me at 3am?

**A:** 
1. Acknowledge within 5 minutes
2. Assess severity
3. If SEV3/SEV4, can wait until morning (add note)
4. If SEV1/SEV2, investigate immediately
5. Escalate if unable to resolve within 30 min

### Q: Do I get comp time for after-hours pages?

**A:** Yes! Log after-hours incidents (>15 min) in comp time sheet. Discuss with manager.

---

## Postmortem Process

### When to Write Postmortem

- **Required:** All SEV1 incidents
- **Required:** SEV2 incidents >1 hour
- **Optional:** SEV3 incidents with learnings

### Postmortem Timeline

1. **Within 24 hours:** Create postmortem document from template
2. **Within 48 hours:** Schedule postmortem meeting (30-60 min)
3. **Within 1 week:** Complete action items assignment
4. **Within 1 month:** Implement top 3 action items

### Postmortem Template

Location: `docs/templates/POSTMORTEM.md`

Required sections:
- Timeline of events
- Root cause analysis (5 whys)
- Impact assessment
- Action items (with owners and deadlines)
- What went well / What went poorly
- Lessons learned

**Remember:** Postmortems are blameless. Focus on systems, not people.

---

## Resources

### Documentation

- [Production Handbook](../PRODUCTION_HANDBOOK.md)
- [SLA Overview](../SLA_OVERVIEW.md)
- [Rollback Runbook](./runbooks/RUNBOOK_ROLLBACK.md)
- [All Playbooks](./playbooks/)

### Dashboards

- [System Health](https://grafana.applylens.io/d/system-health)
- [SLO Compliance](https://grafana.applylens.io/d/slo-compliance)
- [Error Budgets](https://grafana.applylens.io/d/error-budget)
- [Agent Performance](https://grafana.applylens.io/d/agent-performance)

### Slack Channels

- `#incidents` - Active incident coordination
- `#alerts` - Automated monitoring alerts
- `#on-call` - On-call discussions
- `#sre` - SRE team channel
- `#deployments` - Deployment notifications

---

**You've got this! 💪**

Questions? Ask in `#on-call` channel anytime.

---

**Document Ownership:** SRE Team  
**Review Frequency:** Quarterly  
**Last Review:** October 17, 2025  
**Feedback:** Post in #sre with suggestions
