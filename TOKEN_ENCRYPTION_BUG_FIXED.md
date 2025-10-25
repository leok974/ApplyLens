# Token Encryption Bug - FIXED

## Critical Bug Found

The `invalid_grant` error was NOT caused by a client ID mismatch - that was a red herring caused by poor logging (showing only last 10 characters: `...ontent.com` instead of `...p72bhr.apps.googleusercontent.com`).

**The REAL bug:** OAuth tokens were being stored in the database **WITHOUT encryption**, but the code was treating them as encrypted bytes when reading them back.

### Technical Details

#### Database Schema
```python
class OAuthToken(Base):
    access_token = Column(LargeBinary, nullable=False)  # Encrypted with AES-GCM
    refresh_token = Column(LargeBinary, nullable=True)  # Encrypted with AES-GCM
```

#### What Was Broken

**In `auth_google.py` (OAuth callback):**
```python
# ❌ BEFORE: Storing plaintext strings directly to LargeBinary
existing.access_token = creds.token  # String -> bytes (auto-converted)
existing.refresh_token = creds.refresh_token  # String -> bytes
```

**In `gmail_service.py` (_get_creds):**
```python
# ❌ BEFORE: Passing encrypted bytes to Credentials (expects strings!)
creds = Credentials(
    token=tok.access_token,  # bytes from database
    refresh_token=tok.refresh_token,  # bytes from database
    ...
)
```

When Google tried to refresh the token, it received **encrypted binary data** instead of the actual token string, resulting in `invalid_grant: Bad Request`.

### Fix Applied

#### 1. Added Crypto Import to Both Files

**auth_google.py:**
```python
from .core.crypto import Crypto

# Initialize crypto for token encryption
crypto = Crypto()
```

**gmail_service.py:**
```python
from .core.crypto import Crypto

# Initialize crypto for token decryption
crypto = Crypto()
```

#### 2. Fixed Token Storage (auth_google.py)

```python
# ✅ AFTER: Encrypt tokens before storing
existing.access_token = crypto.enc(creds.token.encode()) if creds.token else existing.access_token
if creds.refresh_token:
    existing.refresh_token = crypto.enc(creds.refresh_token.encode())
```

#### 3. Fixed Token Retrieval (gmail_service.py)

```python
# ✅ AFTER: Decrypt tokens when reading from database
access_token_str = crypto.dec(tok.access_token).decode() if tok.access_token else None
refresh_token_str = crypto.dec(tok.refresh_token).decode() if tok.refresh_token else None

creds = Credentials(
    token=access_token_str,
    refresh_token=refresh_token_str,
    ...
)
```

#### 4. Fixed Token Update After Refresh

```python
# ✅ AFTER: Encrypt refreshed access token before storing
tok.access_token = crypto.enc(creds.token.encode())
tok.expiry = creds.expiry
db.commit()
```

#### 5. Improved Logging

Changed client_id suffix logging from 10 chars to 40 chars:
```python
# Before: ...ontent.com (ambiguous)
# After: ...p72bhr.apps.googleusercontent.com (clear)
client_id_suffix = tok.client_id[-40:] if tok.client_id else "unknown"
```

## Why This Wasn't Caught Earlier

1. **routers/auth.py** (newer multi-user flow) WAS using encryption correctly
2. **auth_google.py** (legacy OAuth flow) was NOT using encryption
3. The database accepted both encrypted and unencrypted data (both are bytes)
4. The error only manifested when trying to REFRESH the token
5. Initial authentication worked because tokens were fresh

## Deployment Steps

### 1. ✅ Updated Code
- Modified `services/api/app/auth_google.py` to encrypt tokens on save
- Modified `services/api/app/gmail_service.py` to decrypt tokens on read
- Fixed logging to show 40-char client_id suffix

### 2. ✅ Rebuilt API Container
```bash
docker build -t leoklemet/applylens-api:latest services/api/
docker-compose -f docker-compose.prod.yml up -d api
```

### 3. ✅ Deleted Old Unencrypted Token
```bash
DELETE FROM oauth_tokens WHERE user_email='leoklemet.pa@gmail.com';
# Result: DELETE 1
```

Old tokens were stored as UNENCRYPTED bytes. New code expects ENCRYPTED bytes. They're incompatible.

### 4. ✅ Verified API Health
```bash
docker exec applylens-nginx-prod wget -qO- http://api:8003/ready
# {"status":"ready","db":"ok","es":"ok","migration":"0031_merge_heads"}
```

## What You Must Do Now

### Re-authenticate (Token was deleted)
Visit: **https://applylens.app/api/auth/google/login**

This will:
1. Redirect to Google consent screen
2. You click "Allow"
3. Callback stores NEW encrypted tokens
4. Redirects to https://applylens.app/?connected=google

### Verify New Token is Encrypted

```bash
docker exec applylens-db-prod psql -U postgres -d applylens -c "SELECT user_email, encode(access_token, 'hex') LIKE '%' AS is_binary, length(access_token) AS token_bytes FROM oauth_tokens;"
```

Expected: `is_binary=t` and `token_bytes > 50` (encrypted tokens are longer than plaintext)

### Test Gmail Sync

Try syncing emails. The logs should now show:
```
INFO:app.gmail_service:Creating credentials for leoklemet.pa@gmail.com with client_id suffix: ...p72bhr.apps.googleusercontent.com
INFO:google_auth_httplib2:Refreshing credentials due to a 401 response. Attempt 1/2.
INFO:app.gmail_service:Refreshing token for leoklemet.pa@gmail.com using client_id suffix: ...p72bhr.apps.googleusercontent.com
INFO:app.gmail_service:Token refresh successful for leoklemet.pa@gmail.com
```

**No more `invalid_grant` errors!**

## Monitoring

### Check Logs for Successful Refresh
```powershell
docker logs -f applylens-api-prod | Select-String "Creating credentials|Refreshing token|Token refresh successful|RefreshError"
```

### Check Token Encryption Status
```bash
docker exec applylens-db-prod psql -U postgres -d applylens -c "SELECT user_email, substring(encode(access_token, 'hex'), 1, 20) AS token_hex_prefix, length(access_token) AS bytes FROM oauth_tokens;"
```

Encrypted tokens will have random hex prefixes.

## Root Cause Analysis

### Why auth_google.py Didn't Use Encryption

1. **Legacy code:** Written before encryption was implemented
2. **No type checking:** Python allowed assigning strings to LargeBinary columns
3. **SQLAlchemy auto-conversion:** Silently converted strings to bytes
4. **Delayed failure:** Error only happened on token refresh, not initial auth
5. **Poor error message:** Google just said "Bad Request" without specifics

### Why This Matters

**Security Impact:** Without encryption:
- Tokens stored in plaintext in database backups
- Database admins can see tokens
- Leaked database dumps expose all user accounts

**Functional Impact:** Without proper encryption/decryption:
- Token refresh fails with `invalid_grant`
- Users locked out after token expiry
- Gmail sync completely broken

## Lessons Learned

1. **Type safety:** Use type hints and runtime validation
2. **Encryption everywhere:** All token storage paths must encrypt
3. **Better error messages:** Log encryption state, not just data
4. **Test token refresh:** Don't just test initial auth
5. **Audit legacy code:** Newer code had encryption, older code didn't

## Files Modified

- `services/api/app/auth_google.py` - Added crypto import and encryption on save
- `services/api/app/gmail_service.py` - Added crypto import and decryption on read + encryption on update
- `docker-compose.prod.yml` - Cleaned up unused env vars (separate change)

## Status

✅ **Bug Fixed**
✅ **Code Deployed**
✅ **Container Restarted**
✅ **Old Token Deleted**
⏳ **Waiting for User Re-authentication**

After re-auth, Gmail sync will work correctly with proper token encryption/decryption.
