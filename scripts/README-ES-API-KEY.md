# Elasticsearch API Key Setup for ApplyLens

This directory contains scripts to create Elasticsearch API keys for ApplyLens with limited, scoped permissions.

## Why API Keys?

Instead of using the root `elastic` user credentials in production:
- **Scoped Permissions**: Keys can be limited to specific indices and operations
- **Easy Rotation**: Revoke and recreate keys without changing passwords
- **Audit Trail**: Track which API key performed which actions
- **Security**: Encoded keys can't be reverse-engineered to get username/password

## Prerequisites

You need:
1. **Elasticsearch cluster endpoint** (Elastic Cloud or self-hosted)
2. **Admin credentials** with `manage_api_key` cluster privilege
3. Access to create API keys (usually the `elastic` superuser)

## Quick Start

### For Windows (PowerShell)

```powershell
# Set environment variables
$env:ES_ENDPOINT = "https://your-deployment.es.us-east-1.aws.elastic-cloud.com:9243"
$env:ES_USER = "elastic"
$env:ES_PASS = "your-elastic-password"

# Run the script
.\scripts\create-es-api-key.ps1
```

### For Linux/Mac (Bash)

```bash
# Set environment variables
export ES_ENDPOINT="https://your-deployment.es.us-east-1.aws.elastic-cloud.com:9243"
export ES_USER="elastic"
export ES_PASS="your-elastic-password"

# Make script executable
chmod +x scripts/create-es-api-key.sh

# Run the script
./scripts/create-es-api-key.sh
```

## What the Scripts Do

1. **Validate Prerequisites**: Check that ES_ENDPOINT, ES_USER, and ES_PASS are set
2. **Create API Key**: POST to `/_security/api_key` with limited role descriptors:
   ```json
   {
     "name": "applylens-api",
     "role_descriptors": {
       "applylens_writer": {
         "cluster": ["monitor"],
         "index": [{
           "names": ["gmail_emails-*"],
           "privileges": ["read", "write", "create", "create_index", "manage"]
         }]
       }
     }
   }
   ```
3. **Save to .env**: Append `ELASTICSEARCH_API_KEY=<encoded>` to `.env` file
4. **Verify**: Test the key with `/_cluster/health` request
5. **Print Summary**: Show key ID, encoded value, and revocation command

## Permissions Granted

The API key has **limited** permissions:

### Cluster Privileges
- `monitor`: View cluster health, stats, and settings (read-only)

### Index Privileges
- **Indices**: `gmail_emails-*` (wildcard pattern)
- **Privileges**:
  - `read`: Query and search emails
  - `write`: Index, update, delete email documents
  - `create`: Create new documents
  - `create_index`: Create new indices matching the pattern
  - `manage`: Manage index settings, mappings, aliases

### What It CANNOT Do
- ❌ Access other indices (e.g., `.security`, `kibana_*`)
- ❌ Delete indices
- ❌ Change cluster settings
- ❌ Create/delete users or roles
- ❌ Manage snapshots or pipelines

## Using the API Key

### In Environment Variables

The script adds to `.env`:
```bash
ELASTICSEARCH_API_KEY=VUlQZVpBQUFBQUV...
```

### In docker-compose.prod.yml

```yaml
services:
  api:
    environment:
      - ELASTICSEARCH_API_KEY=${ELASTICSEARCH_API_KEY}
```

### In Python Code

```python
from elasticsearch import Elasticsearch

# Option 1: API Key auth
es = Elasticsearch(
    ["https://your-deployment.es.us-east-1.aws.elastic-cloud.com:9243"],
    api_key=os.getenv("ELASTICSEARCH_API_KEY")
)

# Option 2: Manual header
es = Elasticsearch(
    ["https://your-deployment.es.us-east-1.aws.elastic-cloud.com:9243"],
    headers={"Authorization": f"ApiKey {os.getenv('ELASTICSEARCH_API_KEY')}"}
)
```

### Manual Testing

```bash
# Test cluster health
curl -H "Authorization: ApiKey $ELASTICSEARCH_API_KEY" \
  "$ES_ENDPOINT/_cluster/health?pretty"

# Test index access
curl -H "Authorization: ApiKey $ELASTICSEARCH_API_KEY" \
  "$ES_ENDPOINT/gmail_emails-*/_search?pretty"
```

## Key Management

### List All API Keys

```bash
curl -u "$ES_USER:$ES_PASS" "$ES_ENDPOINT/_security/api_key?pretty"
```

### Get Specific Key Info

```bash
curl -u "$ES_USER:$ES_PASS" \
  "$ES_ENDPOINT/_security/api_key?id=<api_key_id>&pretty"
```

### Revoke a Key

```bash
# Using the ID from script output
curl -X DELETE "$ES_ENDPOINT/_security/api_key" \
  -u "$ES_USER:$ES_PASS" \
  -H "Content-Type: application/json" \
  -d '{"ids": ["<api_key_id>"]}'
```

PowerShell:
```powershell
$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${env:ES_USER}:${env:ES_PASS}"))
$headers = @{
    "Authorization" = "Basic $base64Auth"
    "Content-Type" = "application/json"
}

Invoke-RestMethod -Uri "$env:ES_ENDPOINT/_security/api_key" `
  -Method Delete `
  -Headers $headers `
  -Body '{"ids": ["<api_key_id>"]}'
```

### Revoke All Keys Named "applylens-api"

```bash
curl -X DELETE "$ES_ENDPOINT/_security/api_key" \
  -u "$ES_USER:$ES_PASS" \
  -H "Content-Type: application/json" \
  -d '{"name": "applylens-api"}'
```

## Troubleshooting

### "Unauthorized" Error

**Cause**: ES_USER or ES_PASS is incorrect
**Fix**: Verify credentials, check Elastic Cloud console

### "insufficient permissions" Error

**Cause**: User doesn't have `manage_api_key` cluster privilege
**Fix**: Use the `elastic` superuser or grant privilege:
```bash
curl -X PUT "$ES_ENDPOINT/_security/role/api_key_manager" \
  -u "elastic:$ES_PASS" \
  -H "Content-Type: application/json" \
  -d '{
    "cluster": ["manage_api_key"]
  }'
```

### API Key Not Working

**Cause**: Key might be expired or revoked
**Check**:
```bash
curl -H "Authorization: ApiKey $ELASTICSEARCH_API_KEY" \
  "$ES_ENDPOINT/_security/_authenticate?pretty"
```

### Connection Refused

**Cause**: ES_ENDPOINT is wrong or cluster is down
**Fix**:
- Verify endpoint in Elastic Cloud console
- Check firewall/network access
- Ensure port (usually 9243 for Cloud, 9200 for self-hosted)

## Best Practices

1. **Rotate Keys Regularly**: Create new keys every 90 days, revoke old ones
2. **One Key Per Environment**: Separate keys for dev, staging, production
3. **Monitor Usage**: Use Elasticsearch audit logs to track API key access
4. **Principle of Least Privilege**: Only grant permissions actually needed
5. **Secure Storage**: Store encoded keys in secrets manager (AWS Secrets, HashiCorp Vault)
6. **Never Commit**: Add `.env` to `.gitignore` (already done in this repo)

## Security Notes

⚠️ **Important**:
- The encoded API key is sensitive - treat it like a password
- Don't commit API keys to git
- Don't log API keys in application logs
- Use environment variables or secrets management
- Revoke compromised keys immediately

## Migration from Username/Password

If currently using `ES_USER` and `ES_PASS` in production:

1. Run this script to create API key
2. Update `docker-compose.prod.yml`:
   ```diff
   - environment:
   -   - ES_URL=http://es:9200
   -   - ES_USER=elastic
   -   - ES_PASS=password
   + environment:
   +   - ES_URL=https://your-cloud.es.elastic-cloud.com:9243
   +   - ELASTICSEARCH_API_KEY=${ELASTICSEARCH_API_KEY}
   ```
3. Update Python code to use `api_key` parameter
4. Test thoroughly in staging
5. Deploy to production
6. Monitor logs for authentication errors

## References

- [Elasticsearch API Keys Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/security-api-create-api-key.html)
- [Python Elasticsearch Client - API Key Auth](https://elasticsearch-py.readthedocs.io/en/latest/api.html#authentication)
- [Elastic Cloud Security](https://www.elastic.co/guide/en/cloud/current/ec-security.html)

---

**Created**: October 22, 2025
**Maintainer**: ApplyLens Team
