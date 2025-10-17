# 📉 Incident: Planner Canary Regression

**Severity:** {{severity}}  
**Planner Version:** {{version}}  
**Regression Type:** Quality Drop

## Summary
{{summary}}

## Trigger
Planner canary `{{version}}` has regressed compared to baseline.

- **Version:** {{version}}
- **Canary Traffic:** {{canary_percent}}%
- **Detection Time:** {{timestamp}}

## Metrics Comparison

| Metric | Canary | Baseline | Delta |
|--------|--------|----------|-------|
{{#metrics}}
| {{name}} | {{canary_value}} | {{baseline_value}} | {{delta}} |
{{/metrics}}

## Impact
- **Users Affected:** ~{{affected_users}} ({{canary_percent}}% of traffic)
- **Severity:** Quality regression may impact user experience

## Suggested Remediation

### Option 1: Rollback (Recommended)
```bash
# Immediately rollback to baseline
curl -X POST /api/active/canaries/planner.{{version}}/rollback
```

This will:
1. Set canary traffic to 0%
2. Route all traffic to baseline
3. Preserve canary deployment for analysis

### Option 2: Analyze Regression
Before rolling back, gather more data:
```bash
# Get detailed metrics
curl /api/guard/planner/{{version}}/analysis

# Compare recent decisions
curl /api/agents/planner/audit?version={{version}}&limit=100
```

### Option 3: Adjust Canary %
If regression is minor, reduce traffic but keep monitoring:
```bash
# Reduce to 5% for extended observation
curl -X POST /api/active/canaries/planner.{{version}}/set-percent \
  -d '{"percent": 5}'
```

## Root Cause Analysis Checklist
- [ ] Review recent model changes
- [ ] Check feature extractor updates
- [ ] Verify training data quality
- [ ] Analyze edge cases in affected decisions
- [ ] Compare against known good checkpoints

## Related Artifacts
- [Canary Dashboard](/canaries/planner/{{version}})
- [Regression Analysis](/api/guard/planner/{{version}}/report)
- [Audit Log](/api/agents/planner/audit?version={{version}})

## Rollback Available
{{#rollback_available}}
✅ Yes - Baseline version preserved
{{/rollback_available}}
{{^rollback_available}}
⚠️ No - Manual intervention required
{{/rollback_available}}

## Assignee
{{#assigned_to}}
@{{assigned_to}}
{{/assigned_to}}
{{^assigned_to}}
_Auto-assign to: planner-oncall_
{{/assigned_to}}

---
**Incident ID:** {{incident_id}}  
**Created:** {{created_at}}  
**Status:** {{status}}
