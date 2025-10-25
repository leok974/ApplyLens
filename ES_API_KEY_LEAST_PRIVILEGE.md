# Least-Privilege API Key - Production Security

## 🔒 **Principle of Least Privilege Applied**

The least-privilege API key follows security best practices by granting **only the permissions needed** for ApplyLens to operate, and nothing more.

---

## 📋 **Key Comparison**

| Version | Key ID | Status | Risk Level |
|---------|--------|--------|------------|
| **Original** | `t1iVDZoBZNl7zqftBUGA` | ❌ Revoked | Low |
| **Enhanced** | `uVibDZoBZNl7zqftzkFo` | ❌ Revoked | ⚠️ Medium |
| **Minimal** | `u1ipDZoBZNl7zqftTkGg` | ✅ Active | ✅ Lowest |

---

## 🎯 **What Changed**

### **Removed Dangerous Privileges**

The enhanced key had `"all"` privilege on indices, which included:

- ❌ **`delete`** - Can delete documents (data loss risk)
- ❌ **`delete_index`** - Can delete entire indices (catastrophic)
- ❌ **`manage`** - Can modify index settings (availability risk)
- ❌ **`manage_aliases`** - Can redirect traffic to wrong indices

### **Kept Only Essential Privileges**

The minimal key has **exactly** what ApplyLens needs:

- ✅ **`read`** - Query and search emails
- ✅ **`write`** - Update email documents
- ✅ **`index`** - Add new email documents
- ✅ **`create`** - Create documents with IDs
- ✅ **`create_index`** - Create new indices (for data ingestion)
- ✅ **`view_index_metadata`** - View mappings and settings (read-only)

---

## 🛡️ **Security Test Results**

### ✅ **Positive Tests** (Should Work)

```powershell
# Test 1: Cluster health (monitor privilege)
$headers = @{"Authorization" = "ApiKey $env:ELASTICSEARCH_API_KEY"}
Invoke-RestMethod -Uri "$env:ES_ENDPOINT/_cluster/health" -Headers $headers
```
**Result**: ✅ **PASSED** - Status: green

```powershell
# Test 2: Index a document (write/index privileges)
Invoke-RestMethod -Uri "$env:ES_ENDPOINT/applylens-test/_doc/1" `
  -Method Post -Headers $headers -Body '{"test": true}' `
  -ContentType "application/json"
```
**Result**: ✅ **PASSED** - Document indexed successfully

### ✅ **Negative Tests** (Should Fail)

```powershell
# Test 3: Delete an index (should be blocked)
Invoke-RestMethod -Uri "$env:ES_ENDPOINT/applylens-test" `
  -Method Delete -Headers $headers
```
**Result**: ✅ **BLOCKED** - Returns 403 Forbidden (correct!)

---

## 📊 **Detailed Permission Matrix**

| Operation | Original | Enhanced | Minimal | Required? |
|-----------|----------|----------|---------|-----------|
| **Cluster** ||||
| Monitor health | ✅ | ✅ | ✅ | ✅ Yes |
| Manage templates | ❌ | ✅ | ✅ | ✅ Yes |
| Manage ILM | ❌ | ✅ | ✅ | ✅ Yes |
| Manage pipelines | ❌ | ✅ | ✅ | ✅ Yes |
| Cluster settings | ❌ | ❌ | ❌ | ❌ No |
| **Index Data** ||||
| Read/Search | ✅ | ✅ | ✅ | ✅ Yes |
| Write/Update | ✅ | ✅ | ✅ | ✅ Yes |
| Index new docs | ✅ | ✅ | ✅ | ✅ Yes |
| Create docs | ✅ | ✅ | ✅ | ✅ Yes |
| Delete docs | ⚠️ | ✅ | ❌ | ❌ No |
| **Index Management** ||||
| Create index | ✅ | ✅ | ✅ | ✅ Yes |
| View metadata | ⚠️ | ✅ | ✅ | ✅ Yes |
| Manage settings | ⚠️ | ✅ | ❌ | ❌ No |
| Manage aliases | ⚠️ | ✅ | ❌ | ❌ No |
| Delete index | ❌ | ✅ | ❌ | ❌ No |

---

## 🚨 **Risk Scenarios Prevented**

### 1. **Accidental Index Deletion**

**Scenario**: Developer runs wrong command in production
```bash
# With enhanced key - DANGEROUS!
curl -X DELETE "$ES_ENDPOINT/gmail_emails-2025-10"
# Result: Entire month of emails deleted 💥
```

**With minimal key**:
```bash
# Returns 403 Forbidden - SAFE!
curl -X DELETE "$ES_ENDPOINT/gmail_emails-2025-10"
# Result: Operation blocked ✅
```

### 2. **Document Deletion Bug**

**Scenario**: Application bug tries to delete documents
```python
# With enhanced key - DATA LOSS!
es.delete(index="gmail_emails-2025-10", id="critical-email")
# Result: Email permanently deleted 💥
```

**With minimal key**:
```python
# Raises elasticsearch.exceptions.AuthorizationException ✅
es.delete(index="gmail_emails-2025-10", id="critical-email")
# Result: Delete blocked by Elasticsearch
```

### 3. **Malicious Actor**

**Scenario**: API key leaked in logs or compromised
```bash
# With enhanced key - CATASTROPHIC!
for index in $(curl -s -H "Authorization: ApiKey $KEY" "$ES/gmail_emails-*/_alias" | jq -r 'keys[]'); do
  curl -X DELETE -H "Authorization: ApiKey $KEY" "$ES/$index"
done
# Result: All email indices deleted 💥
```

**With minimal key**:
```bash
# Every DELETE returns 403 - CONTAINED!
# Result: No indices can be deleted ✅
```

---

## 🔧 **Production Deployment**

### Current Status
- **Key ID**: `u1ipDZoBZNl7zqftTkGg`
- **Name**: `applylens-api-minimal`
- **Encoded**: `dTFpcERab0JaTmw3enFmdFRrR2c6TUFWQVBzUVVYc3Y5eFdVajBXdGhBdw==`
- **Location**: `.env` file as `ELASTICSEARCH_API_KEY`
- **Old Keys**: Revoked (original + enhanced)

### Restart Required

```powershell
# Restart API to use new key
docker-compose -f docker-compose.prod.yml restart api
```

### Verification

```powershell
# 1. Check API is using the key
docker logs applylens-api-prod --tail 50 | Select-String "Elasticsearch"

# 2. Test write works
curl -H "Authorization: ApiKey $env:ELASTICSEARCH_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST "$env:ES_ENDPOINT/applylens-test/_doc/1" \
  -d '{"test": "write_check"}'

# 3. Verify delete is blocked
curl -X DELETE -H "Authorization: ApiKey $env:ELASTICSEARCH_API_KEY" \
  "$env:ES_ENDPOINT/applylens-test" -w "%{http_code}"
# Should return 403
```

---

## 📖 **When You Might Need More Permissions**

### Scenarios Requiring Higher Privileges

| Need | Current Key | Solution |
|------|-------------|----------|
| **Delete old emails** | ❌ Can't delete docs | Add `delete` privilege |
| **Drop test indices** | ❌ Can't delete indices | Manual admin operation |
| **Change shard count** | ❌ Can't manage settings | Manual admin operation |
| **Reindex to new alias** | ❌ Can't manage aliases | Manual admin operation |

### How to Temporarily Elevate

```bash
# DON'T: Give app permanent admin access
# DO: Use admin credentials for one-time operations

# Example: Delete old indices (as admin)
curl -u "elastic:$ES_PASS" \
  -X DELETE "$ES_ENDPOINT/applylens-test-*"
```

---

## 🔄 **Key Rotation Schedule**

For production security:

- **Review**: Every 30 days
- **Rotate**: Every 90 days
- **Revoke on compromise**: Immediately

### Rotation Process

```powershell
# 1. Create new key
.\scripts\create-es-api-key-minimal.ps1

# 2. Update .env with new encoded value

# 3. Restart services
docker-compose -f docker-compose.prod.yml restart api

# 4. Verify services are healthy
docker-compose -f docker-compose.prod.yml ps

# 5. Revoke old key (wait 24h to ensure no issues)
curl -u "$ES_USER:$ES_PASS" \
  -X DELETE "$ES_ENDPOINT/_security/api_key" \
  -H "Content-Type: application/json" \
  -d '{"ids": ["OLD_KEY_ID"]}'
```

---

## ✅ **Compliance Benefits**

Least-privilege API keys help with:

- ✅ **SOC 2** - Demonstrates access controls
- ✅ **ISO 27001** - Principle of least privilege
- ✅ **GDPR** - Minimize data access
- ✅ **PCI DSS** - Restrict access to cardholder data
- ✅ **HIPAA** - Minimum necessary access

---

## 📚 **References**

- [Elasticsearch Security Privileges](https://www.elastic.co/guide/en/elasticsearch/reference/current/security-privileges.html)
- [API Key Authentication](https://www.elastic.co/guide/en/elasticsearch/reference/current/security-api-create-api-key.html)
- [Least Privilege Principle (OWASP)](https://owasp.org/www-community/Access_Control#principle-of-least-privilege)

---

**Created**: October 22, 2025
**Status**: ✅ Active in Production
**Security Level**: 🔒 Least Privilege (Recommended)
**Next Review**: January 20, 2026
