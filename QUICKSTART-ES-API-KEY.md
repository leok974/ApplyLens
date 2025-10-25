# Quick Start: Create Elasticsearch API Key

## For Your Use Case (Windows PowerShell)

```powershell
# 1. Set your Elasticsearch Cloud credentials
$env:ES_ENDPOINT = "https://YOUR-DEPLOYMENT.es.us-east-1.aws.elastic-cloud.com:9243"
$env:ES_USER = "elastic"
$env:ES_PASS = "your-password"

# 2. Run the script
.\scripts\create-es-api-key.ps1

# 3. The script will:
#    ✓ Create an API key with limited permissions (gmail_emails-* indices only)
#    ✓ Add ELASTICSEARCH_API_KEY to .env file
#    ✓ Verify the key works by checking cluster health
#    ✓ Print the encoded key and ID for your records

# 4. Expected output:
# API Key created successfully:
# {
#   "id": "abc123...",
#   "name": "applylens-api",
#   "api_key": "xyz789...",
#   "encoded": "VUlQZVpBQUFBQUV..."  <-- This is what gets added to .env
# }

# 5. Verify it's in .env:
Get-Content .env | Select-String "ELASTICSEARCH_API_KEY"

# Output: ELASTICSEARCH_API_KEY=VUlQZVpBQUFBQUV...
```

## What Permissions Does the Key Have?

**Cluster**:
- `monitor` - View cluster health (read-only)

**Indices**: `gmail_emails-*`
- `read` - Search and query
- `write` - Index, update, delete documents
- `create` - Create new documents
- `create_index` - Create new indices
- `manage` - Manage mappings and settings

**Cannot**:
- ❌ Access other indices
- ❌ Delete indices
- ❌ Manage users or security
- ❌ Change cluster settings

## Using the Key

### In Docker Compose
```yaml
services:
  api:
    environment:
      - ELASTICSEARCH_API_KEY=${ELASTICSEARCH_API_KEY}
```

### In Python
```python
from elasticsearch import Elasticsearch
import os

es = Elasticsearch(
    ["https://your-cluster.es.elastic-cloud.com:9243"],
    api_key=os.getenv("ELASTICSEARCH_API_KEY")
)
```

### Testing with cURL
```bash
curl -H "Authorization: ApiKey $ELASTICSEARCH_API_KEY" \
  "$ES_ENDPOINT/_cluster/health?pretty"
```

## Common Issues

### "ES_ENDPOINT is not set"
**Fix**: Set the environment variable with your Elastic Cloud endpoint
```powershell
$env:ES_ENDPOINT = "https://YOUR-ID.es.REGION.aws.elastic-cloud.com:9243"
```

### "Unauthorized" (401)
**Fix**: Check your `elastic` user password
```powershell
$env:ES_PASS = "correct-password"
```

### "Insufficient permissions"
**Fix**: Use the `elastic` superuser account, or grant `manage_api_key` to your user

## Revoking the Key

If compromised or no longer needed:

```powershell
# Get the key ID from the script output, then:
$env:ES_ENDPOINT = "https://YOUR-DEPLOYMENT.es.elastic-cloud.com:9243"
$env:ES_USER = "elastic"
$env:ES_PASS = "your-password"

$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$($env:ES_USER):$($env:ES_PASS)"))
$headers = @{
    "Authorization" = "Basic $base64Auth"
    "Content-Type" = "application/json"
}

# Replace YOUR_KEY_ID with the actual ID
Invoke-RestMethod -Uri "$env:ES_ENDPOINT/_security/api_key" `
  -Method Delete `
  -Headers $headers `
  -Body '{"ids": ["YOUR_KEY_ID"]}'
```

## Security Best Practices

1. ✅ **Never commit** `.env` to git (already in `.gitignore`)
2. ✅ **Rotate keys** every 90 days
3. ✅ **Use separate keys** for dev/staging/production
4. ✅ **Revoke immediately** if compromised
5. ✅ **Store securely** (AWS Secrets Manager, Azure Key Vault, etc.)

## Next Steps

After creating the key:
1. ✅ Update `docker-compose.prod.yml` to use `ELASTICSEARCH_API_KEY`
2. ✅ Update Python code to use API key auth instead of username/password
3. ✅ Test in staging environment
4. ✅ Deploy to production
5. ✅ Monitor logs for authentication errors

---

**Full Documentation**: See `scripts/README-ES-API-KEY.md`
