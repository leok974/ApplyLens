"""
E2E test for complete approvals workflow.

Tests the full flow: propose → list → approve/reject → execute
with mocked database and executors.
"""

from typing import Any, Dict, List
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_full_approvals_flow(async_client):
    """Test complete workflow: propose → list → approve → reject → execute."""

    # In-memory store for test data
    store = {"rows": [], "next_id": 1}

    # Mock database functions
    def mock_bulk_insert(rows: List[Dict[str, Any]]):
        for row in rows:
            row_with_id = {"id": store["next_id"], **row, "status": "proposed"}
            store["rows"].append(row_with_id)
            store["next_id"] += 1

    def mock_get(status="proposed", limit=200):
        return [
            {
                "id": r["id"],
                "email_id": r["email_id"],
                "action": r["action"],
                "policy_id": r["policy_id"],
                "confidence": r["confidence"],
                "rationale": r.get("rationale", ""),
                "params": r.get("params", {}),
                "status": r["status"],
                "created_at": "2025-10-10T00:00:00Z",
            }
            for r in store["rows"]
            if r["status"] == status
        ][:limit]

    def mock_update_status(ids: List[int], status: str):
        for row in store["rows"]:
            if row["id"] in ids:
                row["status"] = status

    # Mock ES audit (no-op)
    def mock_emit_audit(doc: Dict[str, Any]):
        pass

    # Mock executors
    async def mock_execute_actions_internal(actions):
        return {"applied": len(actions)}

    async def mock_perform_unsubscribe(headers):
        return {"result": "success"}

    # Apply patches
    with (
        patch("app.db.approvals_bulk_insert", mock_bulk_insert),
        patch("app.db.approvals_get", mock_get),
        patch("app.db.approvals_update_status", mock_update_status),
        patch("app.logic.audit_es.emit_audit", mock_emit_audit),
        patch(
            "app.routers.approvals.execute_actions_internal",
            mock_execute_actions_internal,
        ),
        patch("app.logic.unsubscribe.perform_unsubscribe", mock_perform_unsubscribe),
    ):
        # Step 1: Propose actions
        propose_payload = {
            "items": [
                {
                    "email_id": "e1",
                    "action": "archive",
                    "policy_id": "promo-expired-archive",
                    "confidence": 0.9,
                    "rationale": "expired promotion",
                },
                {
                    "email_id": "e2",
                    "action": "unsubscribe",
                    "policy_id": "unsubscribe-stale",
                    "confidence": 0.85,
                    "rationale": "stale newsletter",
                    "params": {
                        "headers": {"List-Unsubscribe": "<https://example.com/unsub>"}
                    },
                },
                {
                    "email_id": "e3",
                    "action": "label",
                    "policy_id": "label-important",
                    "confidence": 0.75,
                    "rationale": "important sender",
                },
            ]
        }

        r = await async_client.post("/approvals/propose", json=propose_payload)
        assert r.status_code == 200
        assert r.json()["accepted"] == 3

        # Step 2: List proposed items
        r = await async_client.get("/approvals/proposed")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 3

        # Extract IDs
        id1, id2, id3 = items[0]["id"], items[1]["id"], items[2]["id"]

        # Step 3: Approve first two, reject third
        r = await async_client.post("/approvals/approve", json={"ids": [id1, id2]})
        assert r.status_code == 200
        assert r.json()["updated"] == 2
        assert r.json()["status"] == "approved"

        r = await async_client.post("/approvals/reject", json={"ids": [id3]})
        assert r.status_code == 200
        assert r.json()["updated"] == 1
        assert r.json()["status"] == "rejected"

        # Step 4: Verify only proposed items remain in proposed list
        r = await async_client.get("/approvals/proposed")
        proposed_items = r.json()["items"]
        assert len(proposed_items) == 0  # All have been approved or rejected

        # Step 5: Execute approved actions
        exec_payload = {
            "items": [
                {
                    "email_id": "e1",
                    "action": "archive",
                    "policy_id": "promo-expired-archive",
                    "confidence": 0.9,
                    "rationale": "expired promotion",
                    "params": {},
                },
                {
                    "email_id": "e2",
                    "action": "unsubscribe",
                    "policy_id": "unsubscribe-stale",
                    "confidence": 0.85,
                    "rationale": "stale newsletter",
                    "params": {
                        "headers": {"List-Unsubscribe": "<https://example.com/unsub>"}
                    },
                },
            ]
        }

        r = await async_client.post("/approvals/execute", json=exec_payload)
        assert r.status_code == 200
        assert r.json()["applied"] == 2


@pytest.mark.asyncio
async def test_propose_empty_items(async_client):
    """Test that proposing empty items returns error."""
    with patch("app.db.approvals_bulk_insert"), patch("app.logic.audit_es.emit_audit"):
        r = await async_client.post("/approvals/propose", json={"items": []})
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_approve_empty_ids(async_client):
    """Test that approving with empty IDs returns error."""
    with (
        patch("app.db.approvals_update_status"),
        patch("app.logic.audit_es.emit_audit"),
    ):
        r = await async_client.post("/approvals/approve", json={"ids": []})
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_reject_empty_ids(async_client):
    """Test that rejecting with empty IDs returns error."""
    with (
        patch("app.db.approvals_update_status"),
        patch("app.logic.audit_es.emit_audit"),
    ):
        r = await async_client.post("/approvals/reject", json={"ids": []})
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_execute_empty_items(async_client):
    """Test that executing with no items returns zero applied."""
    with patch("app.logic.audit_es.emit_audit"):
        r = await async_client.post("/approvals/execute", json={"items": []})
        assert r.status_code == 200
        assert r.json()["applied"] == 0


@pytest.mark.asyncio
async def test_list_proposed_with_limit(async_client):
    """Test listing proposed items with custom limit."""

    def mock_get(status="proposed", limit=200):
        return [
            {
                "id": i,
                "email_id": f"e{i}",
                "action": "archive",
                "policy_id": "p1",
                "confidence": 0.9,
                "rationale": "",
                "params": {},
                "status": "proposed",
                "created_at": "2025-10-10T00:00:00Z",
            }
            for i in range(min(limit, 100))
        ]

    with patch("app.db.approvals_get", mock_get):
        # Request with limit 50
        r = await async_client.get("/approvals/proposed?limit=50")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 50


@pytest.mark.asyncio
async def test_execute_splits_actions_by_type(async_client):
    """Test that execute correctly routes different action types."""
    mail_executed = []
    unsub_executed = []

    async def mock_execute_mail(actions):
        mail_executed.extend(actions)
        return {"applied": len(actions)}

    async def mock_perform_unsub(headers):
        unsub_executed.append(headers)
        return {"result": "success"}

    with (
        patch("app.logic.audit_es.emit_audit"),
        patch("app.routers.approvals.execute_actions_internal", mock_execute_mail),
        patch("app.logic.unsubscribe.perform_unsubscribe", mock_perform_unsub),
    ):
        exec_payload = {
            "items": [
                {
                    "email_id": "e1",
                    "action": "archive",
                    "policy_id": "p1",
                    "confidence": 0.9,
                },
                {
                    "email_id": "e2",
                    "action": "unsubscribe",
                    "policy_id": "p2",
                    "confidence": 0.85,
                    "params": {"headers": {"List-Unsubscribe": "<http://ex.com>"}},
                },
                {
                    "email_id": "e3",
                    "action": "label",
                    "policy_id": "p3",
                    "confidence": 0.8,
                },
            ]
        }

        r = await async_client.post("/approvals/execute", json=exec_payload)
        assert r.status_code == 200

        # Verify mail actions were routed correctly (archive + label)
        assert len(mail_executed) == 2
        assert any(a["action"] == "archive" for a in mail_executed)
        assert any(a["action"] == "label" for a in mail_executed)

        # Verify unsubscribe was routed correctly
        assert len(unsub_executed) == 1


@pytest.mark.asyncio
async def test_propose_audit_to_elasticsearch(async_client):
    """Test that proposed actions are audited to ES."""
    audited_docs = []

    def mock_emit(doc):
        audited_docs.append(doc)

    def mock_bulk_insert(rows):
        pass  # No-op

    with (
        patch("app.db.approvals_bulk_insert", mock_bulk_insert),
        patch("app.logic.audit_es.emit_audit", mock_emit),
    ):
        r = await async_client.post(
            "/approvals/propose",
            json={
                "items": [
                    {
                        "email_id": "e1",
                        "action": "archive",
                        "policy_id": "p1",
                        "confidence": 0.9,
                        "rationale": "test",
                    }
                ]
            },
        )

        assert r.status_code == 200

        # Verify ES audit was called
        assert len(audited_docs) == 1
        doc = audited_docs[0]
        assert doc["email_id"] == "e1"
        assert doc["action"] == "archive"
        assert doc["actor"] == "agent"
        assert doc["status"] == "proposed"
        assert doc["policy_id"] == "p1"
        assert doc["confidence"] == 0.9


@pytest.mark.asyncio
async def test_approve_audit_to_elasticsearch(async_client):
    """Test that approval actions are audited to ES."""
    audited_docs = []

    def mock_emit(doc):
        audited_docs.append(doc)

    def mock_update(ids, status):
        pass  # No-op

    with (
        patch("app.db.approvals_update_status", mock_update),
        patch("app.logic.audit_es.emit_audit", mock_emit),
    ):
        r = await async_client.post("/approvals/approve", json={"ids": [1, 2, 3]})

        assert r.status_code == 200

        # Verify ES audit was called for each approval
        assert len(audited_docs) == 3
        for doc in audited_docs:
            assert doc["action"] == "approval"
            assert doc["actor"] == "user"
            assert doc["status"] == "approved"
