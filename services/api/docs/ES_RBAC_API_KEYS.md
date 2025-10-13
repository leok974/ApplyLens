# Elasticsearch RBAC with API Keys

Guide for setting up minimal role-based access control for the ApplyLens application using ES API keys.

## Overview

Instead of using the elastic superuser, create a dedicated API key with minimal required permissions:

- **emails_v1**: Read-only access
- **actions_audit_v1**: Write access for audit logging

## Create API Key

```bash
# Set your Elasticsearch credentials
export ELASTIC_PASSWORD="your-password"
export ES_URL="http://localhost:9200"

# Create the API key
curl -s -u elastic:$ELASTIC_PASSWORD \
  -X POST "$ES_URL/_security/api_key" \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "agentic-mailbox-app",
  "role_descriptors": {
    "app_role": {
      "cluster": ["monitor"],
      "indices": [
        {
          "names": ["emails_v1*"],
          "privileges": ["read", "view_index_metadata"]
        },
        {
          "names": ["actions_audit_v1*"],
          "privileges": ["create", "create_doc", "index", "read"]
        }
      ]
    }
  }
}' | jq .
```text

## Response Format

```json
{
  "id": "VuaCfGcBCdbkQm-e5aOx",
  "name": "agentic-mailbox-app",
  "api_key": "ui2lp2axTNmsyakw9tvNnw",
  "encoded": "VnVhQ2ZHY0JDZGJrUW0tZTVhT3g6dWkybHAyYXhUTm1zeWFrdzl0dk5udw=="
}
```text

## Configure Application

### Option 1: Using Encoded Key (Recommended)

```bash
# Set environment variable
export ES_API_KEY="VnVhQ2ZHY0JDZGJrUW0tZTVhT3g6dWkybHAyYXhUTm1zeWFrdzl0dk5udw=="
```text

In your application settings:

```python
# app/settings.py
ES_API_KEY = os.getenv("ES_API_KEY", None)

# app/logic/search.py
def es_client():
    if ES_API_KEY:
        return Elasticsearch(
            ES_URL,
            api_key=ES_API_KEY
        )
    else:
        return Elasticsearch(ES_URL)
```text

### Option 2: Using ID:Key Format

```bash
export ES_API_KEY="VuaCfGcBCdbkQm-e5aOx:ui2lp2axTNmsyakw9tvNnw"
```text

## Verify API Key

```bash
# Test with curl
curl -H "Authorization: ApiKey VnVhQ2ZHY0JDZGJrUW0tZTVhT3g6dWkybHAyYXhUTm1zeWFrdzl0dk5udw==" \
  "$ES_URL/emails_v1/_search?size=1"

# Should return results (read access works)

curl -H "Authorization: ApiKey VnVhQ2ZHY0JDZGJrUW0tZTVhT3g6dWkybHAyYXhUTm1zeWFrdzl0dk5udw==" \
  -X POST "$ES_URL/actions_audit_v1/_doc" \
  -H 'Content-Type: application/json' \
  -d '{"test": "write access"}'

# Should succeed (write access works)
```text

## Privilege Breakdown

### Cluster Privileges

- **monitor**: Allows health checks and basic cluster info

### Index Privileges

**emails_v1 (Read-Only)**:

- `read`: Search and get documents
- `view_index_metadata`: View index settings and mappings

**actions_audit_v1 (Write + Read)**:

- `create`: Create new documents (POST without ID)
- `create_doc`: Alias for create
- `index`: Index documents (PUT with ID)
- `read`: Read back audit logs

## Rotate API Key

```bash
# Create new key
curl -s -u elastic:$ELASTIC_PASSWORD \
  -X POST "$ES_URL/_security/api_key" \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "agentic-mailbox-app-v2",
  "role_descriptors": { ... }
}' | jq .

# Update application config
export ES_API_KEY="<new_encoded_key>"

# Invalidate old key
curl -u elastic:$ELASTIC_PASSWORD \
  -X DELETE "$ES_URL/_security/api_key" \
  -H 'Content-Type: application/json' \
  -d '{
  "ids": ["VuaCfGcBCdbkQm-e5aOx"]
}'
```text

## List Active API Keys

```bash
curl -u elastic:$ELASTIC_PASSWORD \
  "$ES_URL/_security/api_key?owner=true" | jq .
```text

## Docker Compose Integration

```yaml
# docker-compose.yml
services:
  api:
    environment:
      - ES_URL=http://es:9200
      - ES_API_KEY=${ES_API_KEY}
```text

Create `.env` file:

```bash
ES_API_KEY=VnVhQ2ZHY0JDZGJrUW0tZTVhT3g6dWkybHAyYXhUTm1zeWFrdzl0dk5udw==
```text

## Security Best Practices

1. **Never commit API keys to git** - Use environment variables or secrets management
2. **Rotate keys regularly** - Every 90 days minimum
3. **Use separate keys per environment** - dev, staging, prod
4. **Monitor key usage** - Check Elasticsearch audit logs
5. **Principle of least privilege** - Only grant necessary permissions
6. **Revoke compromised keys immediately** - Use DELETE API

## Troubleshooting

### 401 Unauthorized

- Check API key is not expired
- Verify encoded format is correct
- Ensure key has not been deleted

### 403 Forbidden

- Check role_descriptors have required privileges
- Verify index name matches pattern (e.g., `emails_v1*`)
- Test with `_cat/indices` to see accessible indices

### Connection Refused

- Verify ES_URL is correct
- Check Elasticsearch is running
- Ensure security is enabled in ES config
