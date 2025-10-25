# Enhanced Elasticsearch API Key - Permissions Comparison

## 🔐 Original API Key Permissions

**Created**: October 22, 2025 (initial)
**Key ID**: `t1iVDZoBZNl7zqftBUGA` (revoked)
**Name**: `applylens-api`

### Cluster Privileges
- ✅ `monitor` - View cluster health, stats, settings (read-only)

### Index Privileges
- **Pattern**: `gmail_emails-*` only
- **Privileges**:
  - `read` - Query and search
  - `write` - Index, update, delete documents
  - `create` - Create new documents
  - `create_index` - Create new indices
  - `manage` - Manage settings, mappings, aliases

### Limitations
- ❌ Only covered Gmail indices (`gmail_emails-*`)
- ❌ Could not manage index templates
- ❌ Could not manage ILM policies
- ❌ Could not manage ingest pipelines
- ❌ Required individual permission grants

---

## ✨ Enhanced API Key Permissions

**Created**: October 22, 2025 (enhanced)
**Key ID**: `uVibDZoBZNl7zqftzkFo` (active)
**Name**: `applylens-api-enhanced`
**Encoded**: `dVZpYkRab0JaTmw3enFmdHprRm86V04wWFY5UC1lWnFoZDBPUG9UMkFidw==`

### Cluster Privileges (Expanded)
- ✅ `monitor` - View cluster health, stats, settings (read-only)
- ✅ `manage_index_templates` - Create, update, delete index templates
- ✅ `manage_ilm` - Manage Index Lifecycle Management policies (data retention)
- ✅ `manage_ingest_pipelines` - Create, update, delete ingest pipelines (data transformation)

### Index Privileges (Comprehensive)
- **Patterns**:
  - `gmail_emails*` - All Gmail email indices
  - `applylens*` - All ApplyLens application indices
  - `.applylens*` - Hidden ApplyLens system indices

- **Privileges**:
  - `all` - **Full access** including:
    - All CRUD operations (create, read, update, delete)
    - Index management (settings, mappings, aliases)
    - Search and aggregations
    - Bulk operations
    - Index lifecycle operations
    - Snapshot/restore for these indices

### What This Enables

#### 1. Index Template Management
```json
// Can now create templates for automatic index configuration
PUT _index_template/applylens-emails-template
{
  "index_patterns": ["gmail_emails-*"],
  "template": {
    "settings": {
      "number_of_shards": 2,
      "number_of_replicas": 1
    },
    "mappings": {
      "properties": {
        "subject": { "type": "text" },
        "from": { "type": "keyword" }
      }
    }
  }
}
```

#### 2. ILM Policy Management
```json
// Can configure automatic data retention
PUT _ilm/policy/applylens-emails-policy
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_age": "30d",
            "max_size": "50gb"
          }
        }
      },
      "delete": {
        "min_age": "365d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

#### 3. Ingest Pipeline Management
```json
// Can create data processing pipelines
PUT _ingest/pipeline/applylens-email-enrichment
{
  "description": "Enrich email documents",
  "processors": [
    {
      "set": {
        "field": "indexed_at",
        "value": "{{_ingest.timestamp}}"
      }
    },
    {
      "lowercase": {
        "field": "from_email"
      }
    }
  ]
}
```

#### 4. Full Index Operations
- ✅ Create, read, update, delete documents
- ✅ Bulk indexing with high performance
- ✅ Complex search and aggregations
- ✅ Index settings modification
- ✅ Mapping updates (where allowed)
- ✅ Alias management
- ✅ Index refresh, flush, clear cache

---

## 📊 Comparison Table

| Feature | Original Key | Enhanced Key |
|---------|--------------|--------------|
| **Cluster Health** | ✅ Read-only | ✅ Read-only |
| **Index Templates** | ❌ No | ✅ Full management |
| **ILM Policies** | ❌ No | ✅ Full management |
| **Ingest Pipelines** | ❌ No | ✅ Full management |
| **Index Patterns** | `gmail_emails-*` only | `gmail_emails*`, `applylens*`, `.applylens*` |
| **Index Permissions** | 5 individual privileges | `all` (comprehensive) |
| **Document CRUD** | ✅ Yes | ✅ Yes |
| **Bulk Operations** | ✅ Limited | ✅ Full |
| **Index Management** | ⚠️ Partial | ✅ Full |
| **Alias Management** | ⚠️ Via `manage` | ✅ Full |
| **Search/Aggregations** | ✅ Yes | ✅ Yes |

---

## 🔒 Security Considerations

### What Enhanced Key CAN Do
- ✅ Full access to ApplyLens and Gmail email indices
- ✅ Manage templates, ILM, and pipelines for these indices
- ✅ View cluster health and stats

### What Enhanced Key CANNOT Do
- ❌ Access other indices (e.g., `.security`, `kibana_*`, other apps)
- ❌ Delete entire indices (requires separate `delete_index` cluster privilege)
- ❌ Manage cluster settings
- ❌ Create/manage users, roles, or API keys
- ❌ Manage snapshots or CCR (cross-cluster replication)
- ❌ Shutdown nodes or cluster

### Production Safety
The enhanced key is **scoped appropriately** for ApplyLens:
- Limited to application-specific index patterns
- Can't affect other applications sharing the cluster
- Can't perform destructive cluster-wide operations
- Suitable for production workloads

---

## 🚀 Migration Guide

### If Using Original Key

1. **No code changes needed** - The encoded key format is the same
2. **Environment variable stays the same** - `ELASTICSEARCH_API_KEY`
3. **Automatic upgrade** - Just restart services to use new key
4. **New capabilities available** - Can now use templates, ILM, pipelines

### Verify New Permissions

```powershell
# Test cluster access
$apiKey = $env:ELASTICSEARCH_API_KEY
$headers = @{"Authorization" = "ApiKey $apiKey"}

# Check cluster health (should work)
Invoke-RestMethod -Uri "$env:ES_ENDPOINT/_cluster/health" -Headers $headers

# List index templates (new capability!)
Invoke-RestMethod -Uri "$env:ES_ENDPOINT/_index_template" -Headers $headers

# List ILM policies (new capability!)
Invoke-RestMethod -Uri "$env:ES_ENDPOINT/_ilm/policy" -Headers $headers

# List ingest pipelines (new capability!)
Invoke-RestMethod -Uri "$env:ES_ENDPOINT/_ingest/pipeline" -Headers $headers
```

---

## 📝 Recommended Next Steps

1. **Update Index Templates** (optional but recommended)
   - Define consistent mappings across Gmail email indices
   - Set optimal shard/replica counts
   - Configure analysis settings

2. **Configure ILM Policy** (optional for data retention)
   - Automatically rotate indices after size/time threshold
   - Delete old emails after retention period
   - Optimize storage costs

3. **Create Ingest Pipelines** (optional for enrichment)
   - Normalize email addresses
   - Extract domains
   - Add timestamps
   - Classify emails

4. **Monitor Usage**
   - Use Elasticsearch audit logs
   - Track API key operations
   - Review index patterns coverage

---

## 🔄 Rollback Plan

If issues arise with enhanced permissions:

```powershell
# Revoke enhanced key
$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("elastic:$env:ES_PASS"))
$headers = @{"Authorization" = "Basic $base64Auth"; "Content-Type" = "application/json"}
Invoke-RestMethod -Uri "$env:ES_ENDPOINT/_security/api_key" `
  -Method Delete -Headers $headers `
  -Body '{"ids": ["uVibDZoBZNl7zqftzkFo"]}'

# Recreate original key with basic permissions
.\scripts\create-es-api-key.ps1
```

---

**Created**: October 22, 2025
**Status**: ✅ Active
**Next Review**: 90 days (January 20, 2026)
