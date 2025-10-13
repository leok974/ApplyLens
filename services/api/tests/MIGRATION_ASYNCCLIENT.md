"""
Migration guide for httpx AsyncClient API changes.

This script documents the required changes for tests using the old AsyncClient pattern.
The conftest.py fixture now provides an async_client fixture using ASGITransport.

BEFORE (httpx < 0.28):
    from httpx import AsyncClient
    from app.main import app

    async def test_something():
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/endpoint")
            assert response.status_code == 200

AFTER (httpx >= 0.28):
    # No imports needed - use the fixture

    async def test_something(async_client):
        response = await async_client.get("/endpoint")
        assert response.status_code == 200

MANUAL REFACTORING STEPS:

1. Remove AsyncClient and app imports from test files
2. Add async_client parameter to test functions
3. Replace `async with AsyncClient(app=app, ...) as ac:` with just using async_client
4. Replace `ac.get(...)` with `async_client.get(...)`

FILES REQUIRING UPDATE
======================

Found 100+ instances of AsyncClient(app=app in test files.

Most common pattern in e2e tests:

- test_expired_promo_cleanup.py (3 instances)
- test_quarantine.py (5 instances)
- test_unsubscribe_execute.py (6 instances)
- test_nl_clean_promos.py (5 instances)
- test_nl_unsubscribe.py (8 instances)
- test_policy_exec_route.py (7 instances)
- test_nl_with_es_helpers.py (11 instances)
- test_approvals_flow.py (9 instances)
- test_unsubscribe_grouped.py (4 instances)
- test_productivity_reminders.py (6 instances)

EXAMPLE REFACTOR
================

BEFORE:

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_healthz():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/healthz")
        assert response.status_code == 200
```text

AFTER:
```python
import pytest

@pytest.mark.asyncio
async def test_healthz(async_client):
    response = await async_client.get("/healthz")
    assert response.status_code == 200
```text

SEMI-AUTOMATED APPROACH:
========================

Run this PowerShell script in services/api/tests:

```powershell
# Find all test files with AsyncClient usage
$files = Get-ChildItem -Recurse -Filter "test_*.py" | 
    Select-String "AsyncClient\(app=app" | 
    Select-Object -ExpandProperty Path -Unique

foreach ($file in $files) {
    Write-Host "File: $file"
    # Manual editing recommended for safety
}
```bash

OR use pytest to identify failing tests:

```bash
pytest -v --tb=short 2>&1 | grep "TypeError.*AsyncClient"
```text

TEMPORARY WORKAROUND:
====================

If you need more time for refactoring, you can temporarily pin httpx:

In services/api/pyproject.toml:

```toml
[project]
dependencies = [
    "httpx>=0.25,<0.28",  # temporary pin
    # ... other deps
]
```text

Then reinstall:
```bash
pip install -e "services/api[test]"
```text

But the fixture approach is the long-term solution.
"""

if __name__ == "__main__":
    print(__doc__)
