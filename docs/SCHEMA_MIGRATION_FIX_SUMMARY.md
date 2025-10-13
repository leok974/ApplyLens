# Schema Migration Fix - Summary

**Date:** October 10, 2025  
**Issue:** Missing `emails.category` column causing backfill job failures  
**Status:** ✅ Fixed and Deployed

---

## Problem

The backfill job (`scripts/backfill_bill_dates.py`) was failing with:

```
psycopg2.errors.UndefinedColumn: column "category" does not exist
```

### Root Cause

1. **Code referenced `emails.category`** in queries
2. **Migration 0007 was referenced** but file never existed
3. **Migration 0008 skipped 0007** (went 0006 → 0008)
4. **Database was missing the column** that code expected

This is a common deployment issue where:

- Code is deployed with queries for new columns
- But migrations haven't been applied to add those columns
- Long-running jobs fail hours into execution

---

## Solution Implemented

### 1. Migration 0009: Add Category Column ✅

**File:** `services/api/alembic/versions/0009_add_emails_category.py`

**Changes:**

- Adds `category` column to `emails` table (nullable text)
- Creates index `ix_emails_category` for efficient filtering
- Backfills category from Gmail `CATEGORY_*` labels if available

**Applied:** `alembic upgrade head`

**Verification:**

```bash
$ docker-compose exec db psql -U postgres -d applylens \
    -c "SELECT version_num FROM alembic_version;"
       version_num        
--------------------------
 0009_add_emails_category

$ docker-compose exec db psql -U postgres -d applylens \
    -c "\d emails" | grep category
 category  | text  |  |  | 
    "ix_emails_category" btree (category)
```

### 2. Schema Guard System ✅

**File:** `services/api/app/utils/schema_guard.py`

**Functions:**

| Function | Purpose |
|----------|---------|
| `require_min_migration(version)` | Ensure DB at minimum version (raises RuntimeError) |
| `require_columns(table, *cols)` | Check specific columns exist (raises RuntimeError) |
| `check_column_exists(table, col)` | Safe column check (returns bool) |
| `get_current_migration()` | Get current migration version |
| `get_migration_info()` | Detailed schema introspection |

**Usage in Scripts:**

```python
from app.utils.schema_guard import require_min_migration

def run():
    """Run the backfill job."""
    # Schema guard: Ensure database has required columns
    try:
        require_min_migration("0009_add_emails_category", "emails.category column")
        print("✓ Database schema validation passed\n")
    except RuntimeError as e:
        print(f"❌ Schema validation failed:\n{e}", file=sys.stderr)
        sys.exit(1)
    
    # Rest of the job...
```

**Benefits:**

- ✅ **Fast fail**: Detects issues in seconds, not hours
- ✅ **Clear errors**: Shows exactly what's wrong and how to fix
- ✅ **Prevents corruption**: Stops before making changes
- ✅ **CI/CD friendly**: Easy to integrate into workflows

### 3. Updated Backfill Script ✅

**File:** `services/api/scripts/backfill_bill_dates.py`

**Changes:**

- Added schema guard at startup
- Fails immediately if schema too old
- Includes helpful error message with upgrade instructions

**Before:**

```python
def run():
    # No schema check - would fail hours later
    dry_run = os.getenv("DRY_RUN", "1") == "1"
    # ...
```

**After:**

```python
def run():
    # Schema guard catches issues immediately
    print("Checking database schema...")
    try:
        require_min_migration("0009_add_emails_category", "emails.category column")
        print("✓ Database schema validation passed\n")
    except RuntimeError as e:
        print(f"❌ Schema validation failed:\n{e}", file=sys.stderr)
        sys.exit(1)
    
    dry_run = os.getenv("DRY_RUN", "1") == "1"
    # ...
```

### 4. Comprehensive Documentation ✅

**File:** `docs/SCHEMA_MIGRATION_GUIDE.md` (530+ lines)

**Contents:**

- Problem statement and explanation
- Schema guard usage examples
- Migration workflow and best practices
- Common migration patterns (add column, backfill, rename)
- Prevention strategies (startup checks, dynamic queries, CI smoke tests)
- Troubleshooting guide
- Pre-deployment checklist

### 5. Tests and Verification ✅

**Unit Tests:** `tests/unit/test_schema_guard.py`

- Test require_min_migration with old/current/future versions
- Test check_column_exists for present/missing columns
- Test require_columns with valid/invalid columns
- Test integration with backfill scripts

**Verification Script:** `scripts/verify_schema_guard.py`

- Manual verification against live database
- Tests all schema guard functions
- Provides detailed output for debugging

**Results:**

```
✓ PASS: Get Current Migration
✓ PASS: Check Column Existence
✓ PASS: Require Minimum Migration
✓ PASS: Require Columns
✓ PASS: Get Migration Info

✓ ALL TESTS PASSED
```

---

## Deployment Checklist

- [x] Migration 0009 created
- [x] Migration tested locally
- [x] Migration applied to database
- [x] Schema guard utility created
- [x] Backfill script updated with guard
- [x] Tests created and passing
- [x] Documentation written
- [x] Changes committed and pushed

---

## Prevention Strategies

To prevent this issue from recurring:

### 1. Always Apply Migrations Before Code

**Deployment order:**

```bash
# 1. Apply migrations FIRST
alembic upgrade head

# 2. Deploy code AFTER
git pull
docker-compose up -d --build
```

### 2. Add Schema Guards to Long-Running Jobs

**Required for:**

- GitHub Actions workflows
- Cron jobs
- Batch processing scripts
- Manual maintenance scripts

**Not required for:**

- FastAPI routes (fail fast on first request)
- Unit tests (use test database)

### 3. Use CI/CD Pre-Checks

Add to GitHub Actions:

```yaml
- name: Check schema version
  run: |
    python -c "
    from app.utils.schema_guard import require_min_migration
    require_min_migration('0009_add_emails_category')
    "
```

### 4. Follow Pre-Deployment Checklist

Before deploying code that uses new columns:

- [ ] Migration file created
- [ ] Migration tested locally
- [ ] Schema guard added to scripts
- [ ] Migration applied to production
- [ ] Code deployed after migration
- [ ] Verification tests run

---

## Files Changed

### Created

- `services/api/alembic/versions/0009_add_emails_category.py` - Migration to add category column
- `services/api/app/utils/schema_guard.py` - Schema guard utility
- `services/api/tests/unit/test_schema_guard.py` - Unit tests
- `services/api/scripts/verify_schema_guard.py` - Verification script
- `docs/SCHEMA_MIGRATION_GUIDE.md` - Comprehensive guide

### Modified

- `services/api/scripts/backfill_bill_dates.py` - Added schema guard

---

## Testing

### Verify Migration Applied

```bash
# Check version
docker-compose exec db psql -U postgres -d applylens \
  -c "SELECT version_num FROM alembic_version;"

# Check column exists
docker-compose exec db psql -U postgres -d applylens \
  -c "\d emails" | grep category
```

### Verify Schema Guard Works

```bash
# Run verification script
docker-compose exec api python scripts/verify_schema_guard.py

# Expected output:
# ✓ ALL TESTS PASSED
```

### Test Backfill Script

```bash
# Dry run with schema guard
docker-compose exec api \
  env DRY_RUN=1 ES_EMAIL_INDEX=gmail_emails_v2 \
  python scripts/backfill_bill_dates.py

# Should see:
# Checking database schema...
# ✓ Database schema validation passed
```

---

## Next Steps

1. **Monitor Production:** Verify backfill jobs run successfully
2. **Add More Guards:** Apply pattern to other scripts
3. **Update CI/CD:** Add schema version checks to workflows
4. **Team Training:** Share migration best practices

---

## Related Documentation

- [SCHEMA_MIGRATION_GUIDE.md](./SCHEMA_MIGRATION_GUIDE.md) - Complete guide
- [Alembic Documentation](https://alembic.sqlalchemy.org/) - Official docs
- [SQLAlchemy Migrations](https://docs.sqlalchemy.org/en/14/orm/extensions/alembic.html) - ORM integration

---

## Commits

1. `62defb1` - fix: Add schema migration for emails.category column
2. `fb9b468` - test: Add schema guard tests and verification script

**Branch:** `more-features`  
**Status:** Pushed to GitHub
