# Observability Stack Migration Plan
## Prometheus/Grafana → Datadog

**Status**: PLANNING ONLY - DO NOT EXECUTE
**Date**: November 25, 2025
**Context**: Datadog became primary observability during Gemini/Datadog hackathon (Nov 2025)

---

## Executive Summary

ApplyLens currently runs **dual observability stacks**:
1. **Datadog** (PRIMARY) - LLM metrics, traces, dashboards, SLOs, monitors
2. **Prometheus + Grafana** (LEGACY) - Historical metrics, some dashboards

This document outlines the plan to safely decommission Prometheus/Grafana once Datadog is fully sufficient, freeing up resources and reducing operational complexity.

**Goal**: Single source of truth for observability = Datadog

---

## Current State

### Active Services

**From `docker-compose.prod.yml`**:

```yaml
# LEGACY - Datadog is primary (as of Nov 2025)
prometheus:
  image: prom/prometheus:v2.55.1
  ports: ["9090:9090"]
  # Scraping /metrics endpoint every 15s
  # 6 alert rules loaded
  # 30-day retention

grafana:
  image: grafana/grafana:11.1.0
  ports: ["3000:3000"]
  # Auto-provisioned dashboards
  # grafana-piechart-panel plugin
  # Prometheus datasource configured

# PRIMARY OBSERVABILITY
dd-agent:  # In hackathon compose
  image: datadog/agent:latest
  # APM traces, DogStatsD metrics, logs
```

### What Prometheus/Grafana Still Does

**Active Integration**:
- ✅ **Scrapes `/metrics` endpoint** on API (FastAPI Prometheus exporter)
- ✅ **Stores 30 days of metrics** (TSDB retention)
- ✅ **6 alert rules** loaded from `infra/prometheus/alerts.yml`
- ✅ **Grafana dashboards** auto-provisioned with Prometheus datasource

**Legacy Dashboards** (from audit):
- `phase3_grafana_dashboard.json` - Phase 3 implementation metrics
- `phase4_grafana_dashboard.json` - Phase 4 integration metrics
- `applylens-overview.json` - System overview

**Alert Rules** (`infra/prometheus/alerts.yml`):
- API high latency
- API error rate
- Elasticsearch health
- Database connections
- (Need to inventory full list)

### What Datadog Currently Covers

**From `hackathon/DATADOG_SETUP.md`**:

✅ **Dashboard**: `vap-jgg-r7t` - ApplyLens Observability Copilot
- LLM latency (p50/p95/p99)
- LLM error rate
- Token usage
- Cost estimates
- Task type breakdown
- Email ingest lag
- SLO compliance
- Security risk detection
- API performance (p95)
- API uptime %

✅ **SLOs**: `d22bff39b3365745bbe3cb7853eaa659`
- Email ingest latency < 5 minutes

✅ **Monitors**: Auto-created from SLO breaches
- Incident auto-creation on violations

✅ **APM Traces**: Full request tracing via `dd-trace-py`

✅ **Metrics**: DogStatsD integration
- `applylens.llm.*` - LLM operations
- `applylens.ingest_*` - Email ingestion
- `applylens.security_*` - Security scoring
- `trace.http.request.*` - API traces

---

## Decision Criteria

### Must Be True Before Decommissioning

#### 1. ✅ Alert Parity
**Status**: Needs audit

- [ ] Inventory all Prometheus alert rules
- [ ] Map each to equivalent Datadog monitor
- [ ] Test Datadog monitor triggers
- [ ] Configure notification channels (email, Slack, PagerDuty)
- [ ] Document any alerts intentionally NOT migrated

**How to verify**:
```bash
# List current Prometheus alerts
cat infra/prometheus/alerts.yml
cat infra/prometheus/agent_alerts.yml

# For each alert, create Datadog monitor equivalent
# Test by simulating alert condition
```

#### 2. ✅ Dashboard Parity
**Status**: Partially complete

- [ ] Inventory actively used Grafana dashboards
- [ ] Identify which are critical vs nice-to-have
- [ ] Recreate critical dashboards in Datadog (or confirm already exist)
- [ ] Test Datadog dashboards with real data
- [ ] Get stakeholder approval on new dashboards

**Already in Datadog**:
- ✅ LLM performance metrics
- ✅ API health & performance
- ✅ Email ingestion metrics
- ✅ Security risk metrics

**May need to add**:
- ⏳ Database performance (if Grafana has this)
- ⏳ Elasticsearch metrics (if Grafana has this)
- ⏳ Infrastructure-level metrics (CPU, memory, disk)

#### 3. ✅ Historical Data Strategy
**Status**: Needs decision

**Options**:
- **A. Export snapshots** - Save final Grafana dashboard screenshots/PDFs
- **B. Keep read-only** - Stop collecting new data but keep Grafana accessible
- **C. Export to storage** - Export Prometheus TSDB to cold storage (S3/GCS)
- **D. Discard** - Accept loss of pre-Datadog historical data

**Recommendation**: Option A (snapshots) + Option C (export if needed for compliance)

**Action**: Document in `docs/archive/grafana/HISTORICAL_DATA.md`

#### 4. ✅ No Hard Dependencies
**Status**: Needs verification

- [ ] Search codebase for hardcoded Grafana URLs
- [ ] Search docs for Grafana/Prometheus references
- [ ] Check if any scripts depend on Prometheus API
- [ ] Verify no external tools scraping Grafana

**Search commands**:
```bash
# Find Grafana references
git grep -i "grafana" --exclude-dir=docs/archive
git grep "localhost:3000"
git grep ":3000"  # Grafana port

# Find Prometheus references
git grep -i "prometheus" --exclude-dir=docs/archive
git grep "localhost:9090"
git grep ":9090"  # Prometheus port
```

---

## Migration Tasks

### Phase 3A: Pre-Migration (Weeks 1-2)

#### Task 1: Inventory & Mapping
**Owner**: Leo
**Effort**: 4 hours

1. **List all Prometheus alerts**:
   ```bash
   cat infra/prometheus/alerts.yml > /tmp/prom-alerts-inventory.txt
   cat infra/prometheus/agent_alerts.yml >> /tmp/prom-alerts-inventory.txt
   ```

2. **List all Grafana dashboards**:
   ```bash
   ls -lh infra/grafana/dashboards/
   ls -lh grafana/  # If exists
   ls -lh docs/archive/grafana/phase*_grafana_dashboard.json
   ```

3. **Create mapping spreadsheet**:
   | Prometheus Alert | Condition | Datadog Monitor | Status |
   |-----------------|-----------|-----------------|--------|
   | api_high_latency | p95 > 1s | Create new | TODO |
   | ... | ... | ... | ... |

   | Grafana Dashboard | Purpose | Datadog Dashboard | Status |
   |------------------|---------|-------------------|--------|
   | phase3 | Phase 3 metrics | N/A (historical) | Skip |
   | applylens-overview | System health | vap-jgg-r7t | ✅ Done |

#### Task 2: Create Missing Datadog Monitors
**Owner**: Leo
**Effort**: 6 hours

For each Prometheus alert:
1. Write equivalent Datadog monitor query
2. Configure thresholds (critical, warning, recovery)
3. Set notification channels
4. Test trigger conditions
5. Document in `hackathon/DATADOG_SETUP.md`

**Example migration**:
```yaml
# Prometheus alert
- alert: APIHighLatency
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
  for: 5m
  annotations:
    summary: "API p95 latency above 1s"
```

→ **Datadog monitor**:
```python
# Create via API or UI
{
  "name": "API High Latency",
  "type": "metric alert",
  "query": "avg(last_5m):p95:trace.http.request.duration{service:applylens-api-prod} > 1",
  "message": "API p95 latency above 1s @slack-oncall",
  "tags": ["service:api", "severity:warning"]
}
```

#### Task 3: Validate Datadog Coverage
**Owner**: Leo
**Effort**: 2 hours

1. Generate traffic (use `traffic_generator.py`)
2. Trigger alert conditions intentionally
3. Verify Datadog monitors fire correctly
4. Verify notifications arrive
5. Document any gaps

---

### Phase 3B: Parallel Operation (Weeks 3-4)

#### Task 4: Run Both Stacks in Parallel
**Owner**: Leo
**Effort**: Ongoing monitoring

**Goal**: Confidence that Datadog catches everything Prometheus did.

**Actions**:
1. Keep Prometheus/Grafana running
2. Monitor both Datadog and Prometheus alerts
3. Compare alert triggers (should match)
4. Log any discrepancies in `docs/OBSERVABILITY_MIGRATION_LOG.md`
5. Fix Datadog monitors if alerts missed

**Duration**: 2-4 weeks minimum (through at least one incident cycle)

---

### Phase 3C: Documentation Update (Week 5)

#### Task 5: Update All Docs
**Owner**: Leo
**Effort**: 4 hours

**Files to update**:
- `README.md` - Update observability section to mention Datadog only
- `docs/PRODUCTION_DEPLOYMENT.md` - Remove Grafana setup steps
- `docs/MONITORING_SETUP.md` - Redirect to `hackathon/DATADOG_SETUP.md`
- `docs/ONCALL_HANDBOOK.md` - Update links to Datadog dashboards/monitors
- `services/api/README.md` - Update metrics documentation

**Archive Prometheus/Grafana docs**:
- Move remaining docs to `docs/archive/grafana/`
- Add `DEPRECATED_*.md` warnings at top of archived files
- Update main docs index to remove Prometheus/Grafana links

---

### Phase 3D: Decommission (Week 6+)

#### Task 6: Export Historical Data (Optional)
**Owner**: Leo
**Effort**: 2 hours

**If compliance or long-term analysis requires historical Prometheus data**:

```bash
# Option A: Export snapshots from Grafana
# Visit each dashboard, export as JSON and PDF

# Option B: Export Prometheus TSDB to cloud storage
cd /path/to/prometheus/data
tar -czf prometheus-metrics-2024-2025.tar.gz *
aws s3 cp prometheus-metrics-2024-2025.tar.gz s3://applylens-backups/observability/
# Or: gsutil cp prometheus-metrics-2024-2025.tar.gz gs://applylens-backups/observability/

# Option C: Use Prometheus remote read API
# Query specific metrics and save to CSV/JSON
```

**Document archive location** in `docs/archive/grafana/HISTORICAL_DATA.md`.

#### Task 7: Stop Prometheus/Grafana Services
**Owner**: Leo
**Effort**: 30 minutes

**DO NOT DELETE FILES - Just stop services**:

```yaml
# docker-compose.prod.yml
# Comment out prometheus and grafana services:

  # prometheus:
  #   image: prom/prometheus:v2.55.1
  #   # ... (service config)

  # grafana:
  #   image: grafana/grafana:11.1.0
  #   # ... (service config)
```

**Deployment**:
```bash
# Rebuild and redeploy
docker-compose -f docker-compose.prod.yml up -d

# Verify only expected services running
docker-compose -f docker-compose.prod.yml ps

# Verify Datadog still collecting metrics
curl http://localhost:8000/metrics  # Should still expose /metrics endpoint
docker logs dd-agent | tail -20     # Verify DogStatsD receiving metrics
```

**Monitor for 24-48 hours** to ensure no unexpected issues.

#### Task 8: Archive Configs
**Owner**: Leo
**Effort**: 1 hour

**After confirming no issues**:

```bash
# Create archive directory
mkdir -p infra/archive/prometheus-grafana-2025-11

# Move configs (keep in git history)
git mv infra/prometheus infra/archive/prometheus-grafana-2025-11/prometheus
git mv infra/grafana infra/archive/prometheus-grafana-2025-11/grafana

# Create README explaining archive
cat > infra/archive/prometheus-grafana-2025-11/README.md <<EOF
# Prometheus/Grafana Archive

**Archived**: November 2025
**Reason**: Migrated to Datadog as primary observability

These configurations were used from 2024-11 to 2025-11.

To restore (if needed):
\`\`\`bash
git mv infra/archive/prometheus-grafana-2025-11/prometheus infra/prometheus
git mv infra/archive/prometheus-grafana-2025-11/grafana infra/grafana
# Uncomment services in docker-compose.prod.yml
\`\`\`

**Historical data**: See docs/archive/grafana/HISTORICAL_DATA.md
**Current observability**: See hackathon/DATADOG_SETUP.md
EOF

# Commit
git add -A
git commit -m "chore: archive Prometheus/Grafana configs after Datadog migration"
```

---

## Optional: Keep /metrics Endpoint

**Recommendation**: KEEP the Prometheus `/metrics` endpoint even after decommissioning Prometheus.

**Why**:
- ✅ Datadog can scrape Prometheus metrics (OpenMetrics format)
- ✅ Other tools may use it (future flexibility)
- ✅ No cost to maintain (FastAPI middleware)
- ✅ Useful for debugging with `curl http://localhost:8000/metrics`

**If you want Datadog to scrape `/metrics`**:

```yaml
# docker-compose.prod.yml - dd-agent service
dd-agent:
  environment:
    - DD_PROMETHEUS_SCRAPE_ENABLED=true
    - DD_PROMETHEUS_SCRAPE_CONFIGS=[{"job_name":"applylens-api","static_configs":[{"targets":["applylens-api-prod:8000"]}]}]
```

**Do NOT remove** `prometheus_client` dependency from `services/api/pyproject.toml`.

---

## Rollback Plan

**If Datadog migration has issues**:

### Immediate Rollback (< 7 days after decommission)

```bash
# 1. Restore docker-compose.prod.yml
git revert <commit-that-removed-prometheus-grafana>

# 2. Redeploy
docker-compose -f docker-compose.prod.yml up -d prometheus grafana

# 3. Verify services
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3000/api/health  # Grafana

# 4. Check dashboards and alerts
```

### Long-term Rollback (> 7 days, configs archived)

```bash
# 1. Restore configs from archive
git mv infra/archive/prometheus-grafana-2025-11/prometheus infra/prometheus
git mv infra/archive/prometheus-grafana-2025-11/grafana infra/grafana

# 2. Uncomment services in docker-compose.prod.yml

# 3. Redeploy
docker-compose -f docker-compose.prod.yml up -d prometheus grafana
```

**Note**: Historical data may be lost unless exported in Task 6.

---

## Success Criteria

### Decommission Complete When:

- [x] All Prometheus alerts have Datadog equivalents
- [x] All critical Grafana dashboards recreated in Datadog (or acknowledged as unnecessary)
- [x] Parallel operation period complete (2-4 weeks, no missed alerts)
- [x] All docs updated to reference Datadog only
- [x] Prometheus/Grafana services stopped in production
- [x] Configs archived with restoration instructions
- [x] Team trained on Datadog UI and alerting
- [x] No incidents or gaps in observability for 30 days post-decommission

### Metrics to Track

**Before Decommission**:
- Number of Prometheus alerts: X
- Number of Grafana dashboards: Y
- Prometheus/Grafana container resource usage: Z CPU/memory

**After Decommission**:
- Number of Datadog monitors: X (should match Prometheus alerts)
- Number of Datadog dashboards: Y (critical ones)
- Freed resources: Z CPU/memory available for other services

**Cost Comparison**:
- Self-hosted Prom/Grafana: ~$0 (but uses VM resources)
- Datadog: $X/month (paid service, but includes APM + logs + traces)

---

## Timeline & Ownership

**Phase**: 3C (Observability Migration)
**Target Start**: After Phase 2 merged + stable for 30 days
**Estimated Duration**: 6-8 weeks
**Owner**: Leo (leok974)
**Stakeholders**: All on-call engineers, DevOps

### Proposed Schedule

| Week | Phase | Tasks | Effort |
|------|-------|-------|--------|
| 1-2 | 3A: Pre-Migration | Inventory, mapping, create Datadog monitors | 12 hours |
| 3-4 | 3B: Parallel | Run both stacks, validate Datadog coverage | 2 hours/week |
| 5 | 3C: Docs | Update all documentation | 4 hours |
| 6 | 3D: Decommission | Export data, stop services, archive configs | 4 hours |
| 7+ | Monitoring | Watch for issues, rollback if needed | Ongoing |

**Total Effort**: ~24-30 hours over 6-8 weeks

**Recommended Start**: 2026 Q1 (after holidays, low-activity period)

---

## References

### Internal Docs
- **Current Setup**: `hackathon/DATADOG_SETUP.md` - Datadog dashboard/SLO/monitor creation
- **Phase 1 Audit**: `docs/REPO_AUDIT_PHASE1.md` - Identified Prom/Grafana as legacy
- **Phase 2 Summary**: `docs/REPO_CLEANUP_PHASE2_SUMMARY.md` - Annotated docker-compose
- **Archive READMEs**: `docs/archive/grafana/README.md` - Grafana deprecation notice

### Prometheus/Grafana Configs
- `infra/prometheus/prometheus.yml` - Scrape config
- `infra/prometheus/alerts.yml` - Alert rules
- `infra/grafana/provisioning/datasources/prom.yml` - Datasource config
- `infra/grafana/dashboards/` - Dashboard JSONs

### Datadog Resources
- **Datadog Docs**: https://docs.datadoghq.com/
- **APM Python**: https://docs.datadoghq.com/tracing/setup_overview/setup/python/
- **Monitor API**: https://docs.datadoghq.com/api/latest/monitors/
- **Dashboard API**: https://docs.datadoghq.com/api/latest/dashboards/

---

## Open Questions

1. **Are there any Grafana dashboards actively used in production?**
   - Action: Survey team, check access logs

2. **Do any external systems depend on Prometheus API?**
   - Action: Audit integrations, search for `localhost:9090` in configs

3. **What is our data retention policy?**
   - Current: Prometheus 30 days
   - Datadog: Configurable (check plan limits)
   - Action: Decide if we need longer retention

4. **Should we keep Prometheus for local development?**
   - Pros: Lightweight, no API keys needed
   - Cons: Divergence from production
   - Recommendation: Use Datadog agent in dev too (with separate env tag)

---

## Approval & Sign-off

**Before starting Phase 3C**, get explicit approval from:

- [ ] **Leo** (owner) - Confirms plan is ready
- [ ] **Team leads** - Approve timeline and resource allocation
- [ ] **On-call engineers** - Trained on Datadog, comfortable with cutover
- [ ] **Finance/Ops** - Approve Datadog costs vs self-hosted savings

**Signature**: _______________
**Date**: _______________

---

**END OF PLANNING DOCUMENT**

**Remember**: This is a PLAN only. Monitor Datadog stability for 30+ days before executing decommission.
