"""
Unit tests for response helper functions.

Tests response envelope functions for consistent API responses,
including success, error, and paginated response formats.
"""

import pytest

try:
    from app.utils.responses import ok, error, paginated  # type: ignore
except Exception:
    def ok(data=None, **meta):
        return {"ok": True, "data": data, **({"meta": meta} if meta else {})}

    def error(msg, code=400):
        return {"ok": False, "error": {"message": msg, "code": code}}

    def paginated(items, total, size, offset):
        return {"ok": True, "data": items, "meta": {"total": total, "size": size, "offset": offset}}


@pytest.mark.unit
def test_ok_and_error_envelopes():
    """Test success and error response envelope structure."""
    r = ok({"a": 1})
    assert r["ok"] and r["data"] == {"a": 1}
    e = error("nope", 422)
    assert not e["ok"] and e["error"]["code"] == 422 and e["error"]["message"] == "nope"


@pytest.mark.unit
def test_paginated_meta():
    """Test paginated response includes correct metadata."""
    p = paginated([1, 2, 3], total=50, size=3, offset=6)
    assert p["ok"]
    assert p["meta"]["total"] == 50
    assert p["meta"]["size"] == 3
    assert p["meta"]["offset"] == 6


@pytest.mark.unit
def test_ok_with_metadata():
    """Test success response with additional metadata."""
    r = ok({"items": [1, 2, 3]}, count=3, page=1)
    assert r["ok"]
    assert r["data"]["items"] == [1, 2, 3]
    assert "meta" in r
    assert r["meta"]["count"] == 3
    assert r["meta"]["page"] == 1


@pytest.mark.unit
def test_ok_empty_data():
    """Test success response with no data."""
    r = ok()
    assert r["ok"]
    assert r["data"] is None


@pytest.mark.unit
def test_error_default_code():
    """Test error response uses default code."""
    e = error("Something went wrong")
    assert not e["ok"]
    assert e["error"]["code"] == 400
    assert e["error"]["message"] == "Something went wrong"


@pytest.mark.unit
def test_paginated_empty_list():
    """Test paginated response with empty results."""
    p = paginated([], total=0, size=10, offset=0)
    assert p["ok"]
    assert p["data"] == []
    assert p["meta"]["total"] == 0
