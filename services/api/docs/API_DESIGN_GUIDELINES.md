# API Design Guidelines

## FastAPI Handler Types: Sync vs Async

**Last Updated:** December 2024
**Status:** Critical - Violation causes production 500 errors

### Rule: Match Handler Type to Database Session Type

All FastAPI route handlers using **SessionLocal** (sync SQLAlchemy) **MUST** be `def`, not `async def`.

```python
# ✅ CORRECT - Sync handler with sync SQLAlchemy
@router.get("/api/opportunities")
def list_opportunities(
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    # Synchronous database queries
    results = db.query(Email).filter(...).all()
    return results

# ❌ WRONG - Async handler with sync operations causes 500 errors
@router.get("/api/opportunities")
async def list_opportunities(  # DO NOT USE async def!
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    # Synchronous database queries (no await)
    results = db.query(Email).filter(...).all()
    return results  # FastAPI fails to serialize response → 500 error
```

### Why This Matters

**Symptom:** Silent 500 Internal Server Error in production with no stack trace in logs.

**Root Cause:** FastAPI cannot properly serialize responses from `async def` handlers that contain only synchronous operations (no `await` statements). When you declare a handler as `async def`, FastAPI expects async operations. If the handler runs synchronous code instead, response serialization fails unpredictably.

**Historical Context:** This issue was discovered in December 2024 when `/api/opportunities` and `/api/resume/current` endpoints returned 500 errors after being "optimized" to async def. All business logic worked in isolation testing, but FastAPI's response handling broke.

### When to Use Async Handlers

Only use `async def` handlers when:

1. **Using async SQLAlchemy** with `AsyncSession` and `await` statements:
   ```python
   @router.get("/items")
   async def get_items(db: AsyncSession = Depends(get_async_db)):
       result = await db.execute(select(Item))
       return result.scalars().all()
   ```

2. **Making async API calls** (httpx, aiohttp):
   ```python
   @router.get("/external")
   async def fetch_external(client: httpx.AsyncClient):
       response = await client.get("https://api.example.com")
       return response.json()
   ```

3. **Running async background tasks**:
   ```python
   @router.post("/process")
   async def start_processing(background_tasks: BackgroundTasks):
       await some_async_operation()
       background_tasks.add_task(async_task)
   ```

### Migration Path

**Current State (2024):** Most routers use sync SQLAlchemy (`SessionLocal`).

**Future Migration:** If/when we migrate to async SQLAlchemy:
1. Create `get_async_db()` dependency with `AsyncSession`
2. Convert all queries to use `await db.execute(...)`
3. Update route handlers to `async def`
4. Update regression tests in `test_routes_resume_opportunities.py`

**Until then:** Keep handlers as `def` with sync SQLAlchemy.

### Testing & CI Protection

**Regression Tests:** `tests/test_routes_resume_opportunities.py`

```python
@pytest.mark.asyncio
async def test_opportunities_smoke_no_500(async_client, auth_headers):
    """Prevent regression to async def with sync SQLAlchemy."""
    resp = await async_client.get("/api/opportunities", headers=auth_headers)
    assert resp.status_code != 500, "Got 500 - check if handler is async def!"
```

These tests fail if someone converts handlers back to `async def`, preventing the issue from reaching production.

**CI Enforcement:** Pre-commit hooks run these tests. Don't bypass them.

### Exception Handling Best Practices

Always wrap route logic in try/except with proper logging:

```python
@router.get("/opportunities")
def list_opportunities(user_email: str = Depends(get_current_user_email)):
    try:
        logger.info(f"list_opportunities called for user_email={user_email}")
        # ... business logic ...
        return results
    except Exception as e:
        logger.exception(f"Error in list_opportunities for user {user_email}: {e}")
        raise HTTPException(status_code=500, detail="Internal error listing opportunities")
```

**Why:** FastAPI/uvicorn/gunicorn can swallow exceptions, making debugging impossible without explicit `logger.exception()` calls.

### References

- **Affected Routers:** `app/routers/opportunities.py`, `app/routers/resume.py`
- **Regression Tests:** `tests/test_routes_resume_opportunities.py`
- **Related Issues:** December 2024 production incidents (versions 0.7.15-0.7.22)

---

## Other API Design Rules

### Authentication

All protected endpoints must use:
```python
from app.deps.user import get_current_user_email

@router.get("/protected")
def protected_endpoint(user_email: str = Depends(get_current_user_email)):
    ...
```

### Response Models

Use Pydantic models for consistent API responses:
```python
class OpportunityResponse(BaseModel):
    id: int
    title: str
    company: str
    # ...

@router.get("/opportunities", response_model=list[OpportunityResponse])
def list_opportunities(...):
    ...
```

### Error Handling

- **4xx errors:** Client mistakes (bad request, unauthorized)
- **5xx errors:** Server errors (always log with `logger.exception()`)
- Never return 500 without logging the full stack trace

### Database Queries

- Use SQLAlchemy ORM for type safety
- Always filter by `owner_email` for multi-tenant data
- Add `.limit()` for potentially large result sets
- Use database indexes on frequently filtered columns
