# ILM Policy for actions_audit_v1 - 7 Day Retention

Keeps the audit index lean by automatically deleting documents older than 7 days.

## Apply the ILM Policy

```bash
# 1. Create the ILM policy
curl -X PUT "http://localhost:9200/_ilm/policy/audit_7d_delete" \
  -H "Content-Type: application/json" \
  -d '{
  "policy": {
    "phases": {
      "hot": { 
        "actions": {} 
      },
      "delete": {
        "min_age": "7d",
        "actions": { 
          "delete": {} 
        }
      }
    }
  }
}'

# 2. Create index template to apply policy automatically
curl -X PUT "http://localhost:9200/_index_template/actions_audit_v1_tpl" \
  -H "Content-Type: application/json" \
  -d '{
  "index_patterns": ["actions_audit_v1*"],
  "template": {
    "settings": {
      "index.lifecycle.name": "audit_7d_delete",
      "index.lifecycle.rollover_alias": "actions_audit_v1"
    }
  }
}'
```

## Verify Policy

```bash
# Check policy exists
curl "http://localhost:9200/_ilm/policy/audit_7d_delete"

# Check index template
curl "http://localhost:9200/_index_template/actions_audit_v1_tpl"

# Check index settings (after creating new index)
curl "http://localhost:9200/actions_audit_v1/_settings"
```

## Alternative Retention Periods

### 30 Day Retention
```json
{
  "policy": {
    "phases": {
      "hot": { "actions": {} },
      "delete": {
        "min_age": "30d",
        "actions": { "delete": {} }
      }
    }
  }
}
```

### 90 Day with Rollover
```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_age": "30d",
            "max_primary_shard_size": "50gb"
          }
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": { "delete": {} }
      }
    }
  }
}
```

## Notes

- **Hot Phase**: Index is actively written to
- **Delete Phase**: Triggered after `min_age` from rollover
- **Rollover**: Creates new index when conditions met (age/size)
- **Template**: Automatically applies policy to new indices matching pattern

For production use, consider adding warm/cold phases for cost optimization.
