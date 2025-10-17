# 🚨 Incident: Invariant Failure

**Severity:** {{severity}}  
**Agent:** {{agent}}  
**Invariant:** {{invariant_name}} (`{{invariant_id}}`)

## Summary
{{summary}}

## Trigger
Invariant `{{invariant_id}}` failed during evaluation run.

- **Task ID:** {{task_id}}
- **Evaluation Run:** #{{eval_result_id}}
- **Timestamp:** {{timestamp}}

## Evidence
{{failure_message}}

### Metrics
```json
{{evidence_json}}
```

## Artifacts
- [View Evaluation Result](/api/eval/results/{{eval_result_id}})
- [View Task Details](/api/eval/tasks/{{task_id}})

## Suggested Remediation

### Option 1: Re-run Evaluation
```bash
# Re-run the specific task
curl -X POST /api/eval/tasks/{{task_id}}/rerun
```

### Option 2: Check Agent Configuration
Review agent configuration for potential misconfigurations:
- Threshold settings
- Model parameters
- Feature extractors

### Option 3: Update Invariant
If the invariant is too strict or outdated:
1. Review invariant definition
2. Adjust thresholds or conditions
3. Re-run evaluation suite

## Related Incidents
- Check for similar failures: [Search incidents](/incidents?key={{invariant_id}})

## Assignee
{{#assigned_to}}
@{{assigned_to}}
{{/assigned_to}}
{{^assigned_to}}
_Unassigned - please triage_
{{/assigned_to}}

---
**Incident ID:** {{incident_id}}  
**Created:** {{created_at}}  
**Status:** {{status}}
