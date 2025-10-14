"""
E2E tests for grouped unsubscribe functionality.
"""

import pytest

import app.routers.unsubscribe as U


@pytest.mark.asyncio
async def test_preview_and_execute_grouped(monkeypatch, async_client):
    """
    Test preview and execution of grouped unsubscribes.

    Scenario:
    - 3 emails: 2 from news.example.com, 1 from alerts.example.org
    - Preview should group them correctly
    - Execute should fan out to individual unsubscribes
    """
    # Mock single unsubscribe executor to avoid network calls
    executed = []

    def mock_unsub(payload):
        executed.append(payload["email_id"])
        return {
            "email_id": payload["email_id"],
            "result": {"performed": "http", "status": 204},
        }

    monkeypatch.setattr(U, "execute_unsubscribe", mock_unsub)

    cands = [
        {
            "email_id": "e1",
            "sender_domain": "news.example.com",
            "headers": {"List-Unsubscribe": "<https://ex.com/u?1>"},
        },
        {
            "email_id": "e2",
            "sender_domain": "news.example.com",
            "headers": {"List-Unsubscribe": "<https://ex.com/u?2>"},
        },
        {
            "email_id": "e3",
            "sender_domain": "alerts.example.org",
            "headers": {"List-Unsubscribe": "<https://org.com/un>"},
        },
    ]

    # Step 1: Preview grouped
    r = await async_client.post("/unsubscribe/preview_grouped", json=cands)
    assert r.status_code == 200

    groups = r.json()["groups"]

    # Should have 2 groups
    assert len(groups) == 2

    # One group has 2 items, one has 1
    doms = {g["domain"]: g["count"] for g in groups}
    assert doms.get("news.example.com") == 2
    assert doms.get("alerts.example.org") == 1

    # Step 2: Execute group against news.example.com (fan-out 2 calls)
    grp = [g for g in groups if g["domain"] == "news.example.com"][0]
    r2 = await async_client.post("/unsubscribe/execute_grouped", json=grp)

    assert r2.status_code == 200
    result = r2.json()
    assert result["applied"] == 2
    assert result["domain"] == "news.example.com"

    # Verify both emails were unsubscribed
    assert "e1" in executed
    assert "e2" in executed


@pytest.mark.asyncio
async def test_empty_domain_filtering(monkeypatch, async_client):
    """
    Test that candidates without sender_domain are filtered out.
    """
    monkeypatch.setattr(U, "execute_unsubscribe", lambda p: {"ok": True})

    cands = [
        {
            "email_id": "e1",
            "sender_domain": "example.com",
            "headers": {"List-Unsubscribe": "<https://ex.com/u>"},
        },
        {
            "email_id": "e2",
            "sender_domain": "",  # Empty domain
            "headers": {"List-Unsubscribe": "<https://ex.com/u>"},
        },
        {
            "email_id": "e3",
            "sender_domain": "example.com",
            "headers": {"List-Unsubscribe": "<https://ex.com/u>"},
        },
    ]

    r = await async_client.post("/unsubscribe/preview_grouped", json=cands)
    assert r.status_code == 200

    groups = r.json()["groups"]

    # Only 1 group (empty domain filtered out)
    assert len(groups) == 1
    assert groups[0]["domain"] == "example.com"
    assert groups[0]["count"] == 2
    assert "e2" not in groups[0]["email_ids"]


@pytest.mark.asyncio
async def test_execute_partial_failure(monkeypatch, async_client):
    """
    Test that execution continues even if some unsubscribes fail.
    """
    call_count = 0

    def mock_unsub_with_failure(payload):
        nonlocal call_count
        call_count += 1
        if payload["email_id"] == "e2":
            raise Exception("Network error")
        return {"ok": True}

    monkeypatch.setattr(U, "execute_unsubscribe", mock_unsub_with_failure)

    payload = {
        "domain": "example.com",
        "email_ids": ["e1", "e2", "e3"],
        "params": {"headers": {"List-Unsubscribe": "<https://ex.com/u>"}},
    }

    r = await async_client.post("/unsubscribe/execute_grouped", json=payload)

    assert r.status_code == 200
    # Should report 2 successful (e1, e3), e2 failed but continued
    assert r.json()["applied"] == 2
    assert call_count == 3  # All 3 were attempted


@pytest.mark.asyncio
async def test_multiple_domains_large_batch(monkeypatch, async_client):
    """
    Test grouping with many emails across multiple domains.
    """
    monkeypatch.setattr(U, "execute_unsubscribe", lambda p: {"ok": True})

    # Generate 50 emails across 5 domains
    cands = []
    domains = ["news.com", "alerts.com", "promo.com", "updates.com", "spam.com"]

    for i in range(50):
        cands.append(
            {
                "email_id": f"e{i}",
                "sender_domain": domains[i % 5],
                "headers": {"List-Unsubscribe": f"<https://unsub.com/{i}>"},
            }
        )

    r = await async_client.post("/unsubscribe/preview_grouped", json=cands)
    assert r.status_code == 200

    groups = r.json()["groups"]

    # Should have 5 groups
    assert len(groups) == 5

    # Each group should have 10 emails
    for g in groups:
        assert g["count"] == 10
        assert len(g["email_ids"]) == 10
