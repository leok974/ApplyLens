# DATABASE_URL Refactoring Guide

**Problem:** The PostgreSQL password contains `!` which causes URL/YAML parsing issues in production.

**Solution:** Build the DATABASE_URL in Python from separate POSTGRES_* environment variables.

---

## Changes Required

### 1. Update `services/api/app/settings.py`

#### Add New Fields (after line 16):

```python
class Settings(BaseSettings):
    # Application
    ENV: str = "dev"
    APP_VERSION: str = "0.4.48"
    API_PORT: int = 8003
    API_PREFIX: str = "/api"
    CORS_ORIGINS: str = "http://localhost:5175"
    DATABASE_URL: Optional[str] = None  # Change to Optional for backward compat
    
    # ... existing fields ...
    
    # PostgreSQL - New separate fields (add after POSTGRES_DB line ~54)
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: str = "applylens"
```

#### Add Property (before `class Config` section, around line 77):

```python
    @property
    def sql_database_url(self) -> str:
        """
        Preferred DB URL builder.
        
        - If DATABASE_URL is set -> use it (dev/local/backward compat)
        - Else build from POSTGRES_* parts (prod / docker)
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        if not self.POSTGRES_PASSWORD:
            raise RuntimeError(
                "POSTGRES_PASSWORD is not set and DATABASE_URL is empty. "
                "Set one of them in your environment."
            )
        
        return (
            f"postgresql://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )
```

### 2. Update `services/api/app/db.py`

**Line 10** - Change:
```python
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
```

**To:**
```python
engine = create_engine(settings.sql_database_url, pool_pre_ping=True)
```

### 3. Update `infra/.env.prod`

**Add these variables:**

```bash
# PostgreSQL Connection (separate vars to avoid ! escaping issues)
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_DB=applylens
POSTGRES_PASSWORD=4c9248fc7d7d477d919ccc431b1bbd36!PgA1

# Remove or comment out old DATABASE_URL if present
# DATABASE_URL=...
```

### 4. Docker Compose (if you have one)

**For `docker-compose.yml` or `docker-compose.prod.yml`:**

Remove DATABASE_URL from environment section, rely on env_file instead:

```yaml
services:
  api:
    image: ghcr.io/leok974/applylens-api:latest
    env_file:
      - infra/.env.prod
    # DO NOT set DATABASE_URL here anymore
    # DO NOT set POSTGRES_* here - let env_file handle it
```

---

## Testing

### 1. Test Locally

```powershell
# Set env vars
$env:POSTGRES_HOST="db"
$env:POSTGRES_PORT="5432"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="4c9248fc7d7d477d919ccc431b1bbd36!PgA1"
$env:POSTGRES_DB="applylens"

# Test in Python
python -c "from app.settings import settings; print(settings.sql_database_url)"
# Expected: postgresql://postgres:4c9248fc7d7d477d919ccc431b1bbd36!PgA1@db:5432/applylens
```

### 2. Test in Container

```powershell
# Restart API with new config
docker restart applylens-api-prod

# Check logs
docker logs applylens-api-prod --tail 50

# Verify no password errors
docker logs applylens-api-prod 2>&1 | Select-String "password authentication failed"
# Should return nothing
```

### 3. Smoke Test

```powershell
# Test API health
curl http://localhost:8003/api/profile/me

# Test database connection
docker exec applylens-api-prod python -c "from app.db import engine; print(engine.connect())"
```

---

## Rollback Plan

If issues occur:

1. **Revert settings.py changes**
2. **Set DATABASE_URL directly** in `.env.prod`:
   ```bash
   DATABASE_URL=postgresql://postgres:URLENCODED_PASSWORD@db:5432/applylens
   ```
3. **Restart API**: `docker restart applylens-api-prod`

---

## Benefits

✅ **No URL encoding needed** - Password can contain `!` without escaping  
✅ **Backward compatible** - Still supports DATABASE_URL for local dev  
✅ **Cleaner separation** - DB config separate from connection string  
✅ **Docker-friendly** - No YAML escaping issues  
✅ **Safer** - Password not visible in connection string logs (if implemented)  

---

## Migration Checklist

- [ ] Update `services/api/app/settings.py` with new fields and property
- [ ] Update `services/api/app/db.py` to use `settings.sql_database_url`
- [ ] Add POSTGRES_* vars to `infra/.env.prod`
- [ ] Remove/comment DATABASE_URL from `.env.prod` (optional)
- [ ] Test locally with environment variables
- [ ] Restart production API container
- [ ] Verify logs show no password errors
- [ ] Run smoke tests (health endpoint, database query)
- [ ] Monitor for 15 minutes for any issues

---

## Notes

- The `!` character in the password is now handled safely in Python
- No percent-encoding (`%21`) needed anymore
- The property checks for non-default DATABASE_URL for backward compatibility
- All existing tests should still pass since DATABASE_URL still works
