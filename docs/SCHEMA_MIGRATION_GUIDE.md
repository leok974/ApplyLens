# Schema Migration and Guard System

This document explains how to safely manage database schema changes and prevent schema-related failures in long-running jobs.

## Problem Statement

When SQL queries reference columns that don't exist in the database, the query fails with errors like:

```
psycopg2.errors.UndefinedColumn: column "category" does not exist
```

This typically happens when:

1. **Code is deployed** with queries referencing new columns
2. **But migrations haven't been applied** to add those columns to the database
3. **Jobs or scripts fail** because the schema doesn't match expectations

## Solution: Schema Guards

We've implemented a **schema guard system** to prevent these issues:

### 1. Migration Files

Each database change requires an Alembic migration file:

```bash
services/api/alembic/versions/0009_add_emails_category.py
```

**Key sections:**

- **`revision`**: Unique migration ID (e.g., `0009_add_emails_category`)
- **`down_revision`**: Previous migration (e.g., `0008_approvals_proposed`)
- **`upgrade()`**: SQL to add columns, indexes, tables
- **`downgrade()`**: SQL to remove them (rollback)

### 2. Schema Guard Utility

**Location:** `services/api/app/utils/schema_guard.py`

**Functions:**

#### `require_min_migration(min_version, friendly_name=None)`

Ensures database is at minimum migration version before proceeding.

```python
from app.utils.schema_guard import require_min_migration

# At the start of a script
require_min_migration("0009_add_emails_category", "emails.category column")
```

**Raises `RuntimeError` if:**

- Database is below required version
- Cannot determine current version
- Includes helpful error message with upgrade instructions

#### `require_columns(table_name, *column_names)`

Checks specific columns exist in a table.

```python
from app.utils.schema_guard import require_columns

# Before using columns
require_columns("emails", "category", "risk_score", "expires_at")
```

**Raises `RuntimeError` if:**

- Any column is missing
- Includes list of missing columns

#### `check_column_exists(table_name, column_name)`

Returns `True` if column exists, `False` otherwise (doesn't raise).

```python
from app.utils.schema_guard import check_column_exists

if check_column_exists("emails", "category"):
    # Use category column
else:
    # Skip or use fallback
```

#### `get_migration_info()`

Returns detailed schema information for debugging:

```python
from app.utils.schema_guard import get_migration_info

info = get_migration_info()
print(f"Current migration: {info['current_migration']}")
print(f"Tables: {list(info['tables'].keys())}")
```

### 3. Usage in Scripts

**Example: `scripts/backfill_bill_dates.py`**

```python
from app.utils.schema_guard import require_min_migration

def run():
    """Run the backfill job."""
    # Schema guard: Ensure database has required columns
    print("Checking database schema...")
    try:
        require_min_migration("0009_add_emails_category", "emails.category column")
        print("✓ Database schema validation passed\n")
    except RuntimeError as e:
        print(f"❌ Schema validation failed:\n{e}", file=sys.stderr)
        sys.exit(1)
    
    # Rest of the script...
```

**Benefits:**

- **Fast fail**: Detects schema issues in seconds, not hours
- **Clear error messages**: Tells operator exactly what's wrong
- **Migration instructions**: Shows how to fix the issue
- **Prevents data corruption**: Stops before making changes

## Migration Workflow

### 1. Create Migration File

```bash
cd services/api

# Auto-generate from model changes
alembic revision --autogenerate -m "Add category to emails"

# Or manually create
alembic revision -m "Add category to emails"
```

**Manual template:**

```python
"""Add category column to emails table

Revision ID: 0009_add_emails_category
Revises: 0008_approvals_proposed
Create Date: 2025-10-10 14:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0009_add_emails_category'
down_revision: Union[str, None] = '0008_approvals_proposed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add category column."""
    op.add_column('emails', sa.Column('category', sa.Text(), nullable=True))
    op.create_index('ix_emails_category', 'emails', ['category'])


def downgrade() -> None:
    """Remove category column."""
    op.drop_index('ix_emails_category', table_name='emails')
    op.drop_column('emails', 'category')
```

### 2. Test Migration Locally

```bash
# Apply migration
cd services/api
alembic upgrade head

# Or in Docker
cd infra
docker-compose exec api alembic upgrade head
```

**Verify:**

```bash
# Check current version
docker-compose exec db psql -U postgres -d applylens -c "SELECT version_num FROM alembic_version;"

# Check column exists
docker-compose exec db psql -U postgres -d applylens -c "\d emails" | grep category
```

### 3. Update Code

Add schema guard to scripts that use new columns:

```python
from app.utils.schema_guard import require_min_migration

def main():
    require_min_migration("0009_add_emails_category")
    # ... rest of code
```

### 4. Deploy to Production

**Order matters!** Always apply migrations **before** deploying new code:

```bash
# 1. Apply migrations FIRST
cd services/api
alembic upgrade head

# 2. Deploy code AFTER
git pull
docker-compose up -d --build
```

**Or in CI/CD:**

```yaml
steps:
  - name: Run migrations
    run: alembic upgrade head
    
  - name: Deploy application
    run: docker-compose up -d --build
```

## Prevention Strategies

### Strategy 1: Schema Version Check at Startup

For long-running jobs (GitHub Actions, cron jobs):

```python
#!/usr/bin/env python3
"""
Backfill job that requires specific schema version.
"""
from app.utils.schema_guard import require_min_migration

def main():
    # Gate the entire job with schema check
    require_min_migration("0009_add_emails_category")
    
    # Now safe to use emails.category
    # ...
```

**Result:** Job fails fast (seconds) instead of hours into execution.

### Strategy 2: Dynamic Column Check

For optional columns that may not exist in all environments:

```python
from app.utils.schema_guard import check_column_exists

def build_query(table: str):
    columns = ["id", "subject", "body_text"]
    
    # Conditionally add optional columns
    if check_column_exists(table, "category"):
        columns.append("category")
    
    if check_column_exists(table, "risk_score"):
        columns.append("risk_score")
    
    return f"SELECT {', '.join(columns)} FROM {table}"
```

**Result:** Query adapts to available schema.

### Strategy 3: CI Smoke Test

Add to CI pipeline to verify schema before running jobs:

```yaml
# .github/workflows/backfill-bills.yml
steps:
  - name: Check schema version
    run: |
      python -c "
      from app.utils.schema_guard import get_migration_info
      info = get_migration_info()
      current = info['current_migration']
      required = '0009_add_emails_category'
      if current < required:
        raise RuntimeError(f'Schema too old: {current} < {required}')
      print(f'✓ Schema version OK: {current}')
      "
  
  - name: Run backfill job
    run: python scripts/backfill_bill_dates.py
```

### Strategy 4: Pre-Deployment Checklist

**Before deploying code that uses new columns:**

- [ ] Migration file created (`alembic/versions/NNNN_*.py`)
- [ ] Migration tested locally (`alembic upgrade head`)
- [ ] Schema guard added to scripts (`require_min_migration`)
- [ ] Migration applied to production
- [ ] Code deployed after migration

## Common Migration Patterns

### Adding Nullable Column

```python
def upgrade() -> None:
    op.add_column('emails', sa.Column('category', sa.Text(), nullable=True))
    op.create_index('ix_emails_category', 'emails', ['category'])
```

**Safe because:** Existing rows get `NULL`, no data loss.

### Adding Non-Nullable Column

```python
def upgrade() -> None:
    # Step 1: Add as nullable
    op.add_column('emails', sa.Column('category', sa.Text(), nullable=True))
    
    # Step 2: Backfill default value
    op.execute("UPDATE emails SET category = 'unknown' WHERE category IS NULL")
    
    # Step 3: Make non-nullable
    op.alter_column('emails', 'category', nullable=False)
```

**Safe because:** Backfill ensures all rows have values before constraint.

### Backfilling from Existing Data

```python
def upgrade() -> None:
    op.add_column('emails', sa.Column('category', sa.Text(), nullable=True))
    
    # Derive category from Gmail labels
    op.execute("""
        UPDATE emails
        SET category = CASE
            WHEN 'CATEGORY_PROMOTIONS' = ANY(labels) THEN 'promotions'
            WHEN 'CATEGORY_SOCIAL' = ANY(labels) THEN 'social'
            WHEN 'CATEGORY_UPDATES' = ANY(labels) THEN 'updates'
            WHEN 'CATEGORY_FORUMS' = ANY(labels) THEN 'forums'
            ELSE 'personal'
        END
        WHERE labels IS NOT NULL AND category IS NULL;
    """)
```

**Safe because:** Populates new column from existing data, no manual work.

### Renaming Column

```python
def upgrade() -> None:
    # Create new column
    op.add_column('emails', sa.Column('new_name', sa.Text(), nullable=True))
    
    # Copy data
    op.execute("UPDATE emails SET new_name = old_name")
    
    # Drop old column (optional, can wait for later migration)
    # op.drop_column('emails', 'old_name')


def downgrade() -> None:
    # Restore old column if dropped
    # op.add_column('emails', sa.Column('old_name', sa.Text()))
    # op.execute("UPDATE emails SET old_name = new_name")
    
    op.drop_column('emails', 'new_name')
```

**Safe because:** Data copied before deletion.

## Troubleshooting

### Error: "column does not exist"

**Symptom:**

```
psycopg2.errors.UndefinedColumn: column "category" does not exist
LINE 1: SELECT id, category FROM emails WHERE ...
```

**Solution:**

1. Check current migration version:

   ```bash
   docker-compose exec db psql -U postgres -d applylens \
     -c "SELECT version_num FROM alembic_version;"
   ```

2. Apply missing migrations:

   ```bash
   docker-compose exec api alembic upgrade head
   ```

3. Verify column exists:

   ```bash
   docker-compose exec db psql -U postgres -d applylens \
     -c "\d emails" | grep category
   ```

### Error: "Schema validation failed"

**Symptom:**

```
❌ Schema validation failed:
Database schema is too old. Current: 0008_approvals_proposed, Required: 0009_add_emails_category
```

**Solution:**
Follow the instructions in the error message:

```bash
cd services/api
alembic upgrade head

# Or in Docker:
cd infra
docker-compose exec api alembic upgrade head
```

### Error: "Cannot determine database migration version"

**Symptom:**

```
RuntimeError: Cannot determine database migration version. alembic_version table may not exist.
```

**Possible causes:**

- Database not initialized
- Connection string incorrect
- Alembic never run on this database

**Solution:**

```bash
# Initialize database
docker-compose exec api alembic upgrade head
```

### Migration Failed Mid-Execution

**Symptom:**

```
ERROR  [alembic.util.messaging] Target database is not up to date.
```

**Solution:**

```bash
# Check current version
docker-compose exec api alembic current

# See migration history
docker-compose exec api alembic history

# If stuck, manually fix:
docker-compose exec db psql -U postgres -d applylens \
  -c "UPDATE alembic_version SET version_num = 'PREVIOUS_GOOD_VERSION';"

# Then re-run
docker-compose exec api alembic upgrade head
```

## Best Practices

### 1. One Migration Per Feature

✅ **Good:**

```
0009_add_emails_category.py       # Adds category column
0010_add_risk_score.py            # Adds risk_score column
```

❌ **Bad:**

```
0009_everything.py                # Adds 10 columns, 5 tables, 20 indexes
```

**Why:** Easier to rollback, debug, and review.

### 2. Make Migrations Reversible

✅ **Good:**

```python
def upgrade() -> None:
    op.add_column('emails', sa.Column('category', sa.Text()))

def downgrade() -> None:
    op.drop_column('emails', 'category')
```

❌ **Bad:**

```python
def upgrade() -> None:
    op.add_column('emails', sa.Column('category', sa.Text()))

def downgrade() -> None:
    pass  # Rollback not implemented
```

**Why:** Enables `alembic downgrade` for rollbacks.

### 3. Test Migrations Locally First

```bash
# Test upgrade
alembic upgrade +1

# Test downgrade
alembic downgrade -1

# Test full cycle
alembic downgrade base
alembic upgrade head
```

### 4. Document Schema Dependencies

In migration docstring:

```python
"""Add category column to emails table

Revision ID: 0009_add_emails_category
Revises: 0008_approvals_proposed
Create Date: 2025-10-10 14:30:00.000000

This migration adds the category column to support email categorization.

**Dependencies:**
- Requires labels column from migration 0002_oauth_gmail
- Backfills category from Gmail CATEGORY_* labels

**Breaking changes:**
- Scripts using emails.category will fail if this migration not applied
- Add schema guard: require_min_migration("0009_add_emails_category")
"""
```

### 5. Use Schema Guards in All Long-Running Jobs

**Required for:**

- GitHub Actions workflows
- Cron jobs
- Manual scripts (`scripts/`)
- Batch processing jobs

**Not required for:**

- FastAPI routes (fail fast on first request)
- Unit tests (use test database)
- Development experiments

## Reference

### Alembic Commands

```bash
# Create new migration
alembic revision -m "description"
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head          # All pending migrations
alembic upgrade +1            # Next migration only
alembic upgrade 0009          # Specific version

# Rollback migrations
alembic downgrade -1          # Previous version
alembic downgrade 0008        # Specific version
alembic downgrade base        # All migrations

# Info commands
alembic current               # Current version
alembic history               # Migration history
alembic show 0009             # Show specific migration
```

### Schema Guard API

```python
# In app/utils/schema_guard.py

require_min_migration(min_version: str, friendly_name: str = None) -> None
    # Raises RuntimeError if database below min_version

require_columns(table_name: str, *column_names: str) -> None
    # Raises RuntimeError if any column missing

check_column_exists(table_name: str, column_name: str) -> bool
    # Returns True if column exists, False otherwise

get_current_migration() -> Optional[str]
    # Returns current migration version or None

get_migration_info() -> dict
    # Returns detailed schema information
```

### Example: Complete Migration + Guard

**1. Create migration:**

```bash
alembic revision -m "Add email automation fields"
```

**2. Edit migration file:**

```python
def upgrade() -> None:
    op.add_column('emails', sa.Column('category', sa.Text()))
    op.add_column('emails', sa.Column('risk_score', sa.Real()))
    op.create_index('ix_emails_category', 'emails', ['category'])

def downgrade() -> None:
    op.drop_index('ix_emails_category', table_name='emails')
    op.drop_column('emails', 'risk_score')
    op.drop_column('emails', 'category')
```

**3. Add schema guard to script:**

```python
from app.utils.schema_guard import require_min_migration

def main():
    require_min_migration("0010_add_email_automation_fields")
    # ... rest of code
```

**4. Apply migration:**

```bash
alembic upgrade head
```

**5. Deploy code:**

```bash
git push
docker-compose up -d --build
```

## Summary

**Key Takeaways:**

1. **Always create migrations** for schema changes
2. **Apply migrations before code** that uses new columns
3. **Add schema guards** to long-running jobs
4. **Test migrations locally** before production
5. **Document dependencies** in migration files

**Remember:** Schema guards are cheap insurance against expensive failures. Add them liberally!
