# 💰 Incident: Budget Exceeded

**Severity:** {{severity}}  
**Budget Key:** {{budget_key}}  
**Overage:** ${{overage}} ({{overage_pct}}%)

## Summary
{{summary}}

## Trigger
Budget limit has been exceeded for `{{budget_key}}`.

- **Spent:** ${{spent}}
- **Limit:** ${{limit}}
- **Overage:** ${{overage}} ({{overage_pct}}% over budget)
- **Timestamp:** {{timestamp}}

## Impact
Continued operation at current spend rate will result in:
- Additional costs of ~${{projected_daily_overage}}/day
- Risk of service degradation if limits enforced

## Suggested Remediation

### Option 1: Reduce Traffic (Immediate)
```bash
# Reduce planner canary split to 0%
curl -X POST /api/active/canaries/{{agent}}/rollback

# Or pause agent entirely
curl -X POST /api/agents/{{agent}}/pause
```

### Option 2: Increase Budget (Approval Required)
If overage is acceptable:
```bash
# Request budget increase
curl -X POST /api/budgets/{{budget_key}}/increase \
  -d '{"new_limit": {{suggested_limit}}, "justification": "..."}'
```

### Option 3: Optimize Usage
- Review expensive operations (LLM calls, API requests)
- Implement caching for repeated queries
- Adjust sampling rates in eval/training

## Cost Breakdown
```
Recent Spend Analysis:
{{cost_breakdown}}
```

## Related Incidents
- [View budget history](/api/budgets/{{budget_key}}/history)
- [Similar incidents](/incidents?kind=budget)

## Assignee
{{#assigned_to}}
@{{assigned_to}}
{{/assigned_to}}
{{^assigned_to}}
_Auto-assign to: budget-oncall_
{{/assigned_to}}

---
**Incident ID:** {{incident_id}}  
**Created:** {{created_at}}  
**Status:** {{status}}
