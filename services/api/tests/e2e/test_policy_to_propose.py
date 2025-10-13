"""
E2E test: Policy engine → Approvals tray integration

Tests the complete flow:
1. Run policy set against ES emails (/policies/run)
2. Receive proposed actions
3. Submit to approvals tray (/approvals/propose)
4. Verify actions appear in /approvals/proposed
"""

import types

import pytest
from httpx import AsyncClient

import app.db as DB
import app.logic.audit_es as AUD
import app.logic.search as S
from app.main import app


@pytest.mark.asyncio
async def test_policy_run_then_propose(monkeypatch):
    """
    Test that policy engine proposals flow correctly into the approvals tray.

    Scenario:
    - 2 promotional emails: 1 expired, 1 valid
    - Policy triggers on expired promotions
    - Proposal fed to approvals tray
    - Verify only expired email is proposed for approval
    """
    # Mock ES search: 1 expired promo, 1 valid promo
    fake_hits = [
        {
            "_id": "exp",
            "_source": {
                "id": "exp",
                "category": "promotions",
                "expires_at": "2025-10-01T00:00:00Z",  # Expired
                "received_at": "2025-10-02T00:00:00Z",
            },
        },
        {
            "_id": "ok",
            "_source": {
                "id": "ok",
                "category": "promotions",
                "expires_at": "2099-01-01T00:00:00Z",  # Valid
                "received_at": "2025-10-02T00:00:00Z",
            },
        },
    ]

    class FakeES:
        def search(self, index, body):
            return {"hits": {"hits": fake_hits}}

    monkeypatch.setattr(S, "es_client", lambda: FakeES())

    # Mock DB approvals table with in-memory store
    store = {"rows": [], "id": 1}

    class MConn:
        autocommit = True

        def cursor(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def execute(self, q, args=None):
            ql = " ".join(q.split()).lower()
            if "insert into approvals_proposed" in ql:
                row = {
                    "id": store["id"],
                    "email_id": args[0],
                    "action": args[1],
                    "policy_id": args[2],
                    "confidence": args[3],
                    "rationale": args[4],
                    "params": args[5],
                    "status": args[6],
                }
                store["rows"].append(row)
                store["id"] += 1
            elif "select id,email_id" in ql:
                self._result = [
                    (
                        r["id"],
                        r["email_id"],
                        r["action"],
                        r["policy_id"],
                        r["confidence"],
                        r["rationale"],
                        r["params"],
                        r["status"],
                        "2025-10-10T00:00:00Z",
                    )
                    for r in store["rows"]
                    if r["status"] == "proposed"
                ]

        @property
        def description(self):
            return [
                ("id",),
                ("email_id",),
                ("action",),
                ("policy_id",),
                ("confidence",),
                ("rationale",),
                ("params",),
                ("status",),
                ("created_at",),
            ]

        def fetchall(self):
            return getattr(self, "_result", [])

    monkeypatch.setattr(
        DB, "psycopg2", types.SimpleNamespace(connect=lambda d: MConn())
    )

    # No-op audit
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: None)

    # Policy payload: Archive expired promotions
    payload_run = {
        "policy_set": {
            "id": "cleanup-promos",
            "policies": [
                {
                    "id": "promo-expired-archive",
                    "if": {
                        "all": [
                            {"field": "category", "op": "=", "value": "promotions"},
                            {"field": "expires_at", "op": "<", "value": "now"},
                        ]
                    },
                    "then": {
                        "action": "archive",
                        "confidence_min": 0.8,
                        "rationale": "expired promotion",
                    },
                }
            ],
        },
        "es_filter": {"term": {"category": "promotions"}},
        "limit": 200,
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Step 1: Run policy engine
        r = await ac.post("/policies/run", json=payload_run)
        assert r.status_code == 200

        actions = r.json()["proposed_actions"]

        # Only expired email should be proposed
        ids = [a["email_id"] for a in actions]
        assert ids == ["exp"], f"Expected ['exp'], got {ids}"

        # Step 2: Feed proposals to approvals tray
        r2 = await ac.post("/approvals/propose", json={"items": actions})
        assert r2.status_code == 200
        assert r2.json()["accepted"] == 1

        # Step 3: Verify action appears in /approvals/proposed
        r3 = await ac.get("/approvals/proposed")
        assert r3.status_code == 200

        proposed = r3.json()["items"]
        assert len(proposed) == 1, f"Expected 1 proposed action, got {len(proposed)}"
        assert proposed[0]["email_id"] == "exp"
        assert proposed[0]["action"] == "archive"
        assert proposed[0]["policy_id"] == "promo-expired-archive"
        assert proposed[0]["status"] == "proposed"


@pytest.mark.asyncio
async def test_multi_policy_proposals(monkeypatch):
    """
    Test multiple policies generating different actions for approval.

    Scenario:
    - 3 emails: expired promo, newsletter, spam
    - 2 policies: archive expired, unsubscribe newsletters
    - Verify 2 different actions proposed
    """
    fake_hits = [
        {
            "_id": "promo",
            "_source": {
                "id": "promo",
                "category": "promotions",
                "expires_at": "2025-10-01T00:00:00Z",
                "received_at": "2025-10-02T00:00:00Z",
            },
        },
        {
            "_id": "news",
            "_source": {
                "id": "news",
                "category": "updates",
                "label_heuristics": ["newsletter_ads"],
                "received_at": "2025-10-02T00:00:00Z",
            },
        },
    ]

    class FakeES:
        def search(self, index, body):
            return {"hits": {"hits": fake_hits}}

    monkeypatch.setattr(S, "es_client", lambda: FakeES())

    store = {"rows": [], "id": 1}

    class MConn:
        autocommit = True

        def cursor(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def execute(self, q, args=None):
            ql = " ".join(q.split()).lower()
            if "insert into approvals_proposed" in ql:
                row = {
                    "id": store["id"],
                    "email_id": args[0],
                    "action": args[1],
                    "policy_id": args[2],
                    "confidence": args[3],
                    "rationale": args[4],
                    "params": args[5],
                    "status": args[6],
                }
                store["rows"].append(row)
                store["id"] += 1
            elif "select id,email_id" in ql:
                self._result = [
                    (
                        r["id"],
                        r["email_id"],
                        r["action"],
                        r["policy_id"],
                        r["confidence"],
                        r["rationale"],
                        r["params"],
                        r["status"],
                        "2025-10-10T00:00:00Z",
                    )
                    for r in store["rows"]
                    if r["status"] == "proposed"
                ]

        @property
        def description(self):
            return [
                ("id",),
                ("email_id",),
                ("action",),
                ("policy_id",),
                ("confidence",),
                ("rationale",),
                ("params",),
                ("status",),
                ("created_at",),
            ]

        def fetchall(self):
            return getattr(self, "_result", [])

    monkeypatch.setattr(
        DB, "psycopg2", types.SimpleNamespace(connect=lambda d: MConn())
    )
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: None)

    payload_run = {
        "policy_set": {
            "id": "cleanup-all",
            "policies": [
                {
                    "id": "promo-expired-archive",
                    "if": {
                        "all": [
                            {"field": "category", "op": "=", "value": "promotions"},
                            {"field": "expires_at", "op": "<", "value": "now"},
                        ]
                    },
                    "then": {
                        "action": "archive",
                        "confidence_min": 0.8,
                        "rationale": "expired promotion",
                    },
                },
                {
                    "id": "newsletter-unsubscribe",
                    "if": {
                        "any": [
                            {
                                "field": "label_heuristics",
                                "op": "contains",
                                "value": "newsletter_ads",
                            }
                        ]
                    },
                    "then": {
                        "action": "unsubscribe",
                        "confidence_min": 0.7,
                        "rationale": "newsletter detected",
                    },
                },
            ],
        },
        "es_filter": {"match_all": {}},
        "limit": 200,
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/policies/run", json=payload_run)
        assert r.status_code == 200

        actions = r.json()["proposed_actions"]
        assert len(actions) == 2, f"Expected 2 actions, got {len(actions)}"

        # Verify different actions for different emails
        action_map = {a["email_id"]: a["action"] for a in actions}
        assert action_map["promo"] == "archive"
        assert action_map["news"] == "unsubscribe"

        # Propose all
        r2 = await ac.post("/approvals/propose", json={"items": actions})
        assert r2.status_code == 200
        assert r2.json()["accepted"] == 2

        # Verify both in tray
        r3 = await ac.get("/approvals/proposed")
        assert r3.status_code == 200

        proposed = r3.json()["items"]
        assert len(proposed) == 2
        email_ids = {p["email_id"] for p in proposed}
        assert email_ids == {"promo", "news"}
