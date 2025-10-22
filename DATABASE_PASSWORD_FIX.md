# Database Password Authentication Fix

## Issue
OAuth callback was failing with 500 Internal Server Error due to database connection failures:
```
psycopg2.OperationalError: connection to server at "db" (172.25.0.3), port 5432 failed:
FATAL:  password authentication failed for user "postgres"
```

## Root Cause
**Problem 1: Special Characters in DATABASE_URL**
- The postgres password contains an exclamation mark: `4c9248fc7d7d477d919ccc431b1bbd36!PgA1`
- In PostgreSQL connection URLs, special characters must be URL-encoded
- The `!` character must be encoded as `%21`
- Original URL: `postgresql://postgres:4c9248fc7d7d477d919ccc431b1bbd36!PgA1@db:5432/applylens`
- Fixed URL: `postgresql://postgres:4c9248fc7d7d477d919ccc431b1bbd36%21PgA1@db:5432/applylens`

**Problem 2: Password Mismatch**
- The database volume was created on October 14, 2025 with an unknown password
- The environment variable `POSTGRES_PASSWORD` only applies during initial database creation
- Changing the env var doesn't update an existing database's password
- The stored password in Postgres didn't match the configured password

## Solutions Implemented

### 1. URL-Encode Special Characters in DATABASE_URL
**File**: `docker-compose.prod.yml`
```yaml
# Before
DATABASE_URL: postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-applylens}

# After (hardcoded URL-encoded password)
# Note: Password contains ! which is URL-encoded as %21
DATABASE_URL: postgresql://${POSTGRES_USER:-postgres}:4c9248fc7d7d477d919ccc431b1bbd36%21PgA1@db:5432/${POSTGRES_DB:-applylens}
```

### 2. Reset Postgres User Password
```bash
docker exec applylens-db-prod psql -U postgres -c "ALTER USER postgres WITH PASSWORD '4c9248fc7d7d477d919ccc431b1bbd36!PgA1';"
```

### 3. Restart API Service
```bash
docker-compose -f docker-compose.prod.yml up -d api
```

## Verification

### Test Database Connection
```bash
# From API container
docker exec applylens-api-prod python -c "
import os
from sqlalchemy import create_engine
engine = create_engine(os.environ['DATABASE_URL'])
conn = engine.connect()
print('✅ Database connection successful')
conn.close()
"
```

**Result**: ✅ Connection successful

### Test OAuth Flow
Navigate to: https://applylens.app/web/welcome
Click "Sign In with Google"

## Special Characters Requiring URL Encoding in PostgreSQL URLs

| Character | URL Encoded |
|-----------|-------------|
| `!`       | `%21`       |
| `@`       | `%40`       |
| `#`       | `%23`       |
| `$`       | `%24`       |
| `%`       | `%25`       |
| `^`       | `%5E`       |
| `&`       | `%26`       |
| `*`       | `%2A`       |
| `(`       | `%28`       |
| `)`       | `%29`       |
| `[`       | `%5B`       |
| `]`       | `%5D`       |
| `{`       | `%7B`       |
| `}`       | `%7D`       |
| `:`       | `%3A`       |
| `;`       | `%3B`       |
| `/`       | `%2F`       |
| `?`       | `%3F`       |
| `=`       | `%3D`       |
| ` ` (space) | `%20` or `+` |

## Best Practices

### 1. Always URL-Encode Database Passwords
When using passwords in connection URLs, always URL-encode special characters:
```python
from urllib.parse import quote_plus
password = "my!pass@word"
encoded_password = quote_plus(password)
db_url = f"postgresql://user:{encoded_password}@host:5432/dbname"
```

### 2. Use Environment Variables with URL Encoding
```yaml
# Option A: Pre-encode in environment variable
POSTGRES_PASSWORD_ENCODED: "4c9248fc7d7d477d919ccc431b1bbd36%21PgA1"
DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD_ENCODED}@db:5432/applylens

# Option B: Use separate host/port/password fields (recommended)
DB_HOST: db
DB_PORT: 5432
DB_USER: postgres
DB_PASSWORD: "4c9248fc7d7d477d919ccc431b1bbd36!PgA1"  # No encoding needed
DB_NAME: applylens
# Then construct URL in application code with proper encoding
```

### 3. Password Change Process for Existing Databases
Changing `POSTGRES_PASSWORD` environment variable doesn't update existing databases:
```bash
# Step 1: Connect to database
docker exec -it <db-container> psql -U postgres

# Step 2: Change password
ALTER USER postgres WITH PASSWORD 'new_password_here';

# Step 3: Update docker-compose.yml with URL-encoded password
# Step 4: Restart services
docker-compose up -d
```

### 4. Secure Password Management
- Store passwords in `.env` files (not committed to git)
- Add `.env` to `.gitignore`
- Use secrets management for production (Docker Secrets, AWS Secrets Manager, etc.)
- Rotate passwords regularly
- Use strong passwords with special characters

## Related Issues
- **OAUTH_TROUBLESHOOTING_SUMMARY.md**: OAuth callback flow issues
- Port mismatch (API on 8000 vs 8003) - resolved
- Health check failures - resolved by disabling curl-based check
- Authorization code reuse (expected OAuth behavior)

## Timeline
- **October 14, 2025**: Database volume created with unknown password
- **October 22, 2025**:
  - Discovered password authentication failure during OAuth flow
  - Fixed DATABASE_URL with URL-encoded password
  - Reset Postgres user password
  - Verified database connection successful
  - OAuth flow ready for testing

## Next Steps
1. ✅ Database connection working
2. ⏳ Test complete OAuth flow end-to-end
3. ⏳ Monitor logs for any remaining issues
4. 💡 Consider migrating to secrets management for production
5. 💡 Implement proper password rotation policy

## References
- [PostgreSQL Connection URLs](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING)
- [SQLAlchemy Database URLs](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls)
- [URL Encoding](https://www.w3schools.com/tags/ref_urlencode.ASP)
- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)
- [Postgres Password Authentication](https://www.postgresql.org/docs/current/auth-password.html)
