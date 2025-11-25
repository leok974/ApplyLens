# Phase 5.5 PR1: Policy Bundle CRUD Tests
# Comprehensive tests for policy bundle CRUD operations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# Sample valid policy rules
VALID_RULES = [
    {
        "id": "triage-quarantine-hi-risk",
        "agent": "inbox.triage",
        "action": "quarantine",
        "effect": "allow",
        "conditions": {">=risk_score": 90, "domain_seen_days": ">30"},
        "reason": "Auto-quarantine high-risk emails from new domains",
        "priority": 80,
        "enabled": True,
        "tags": ["security", "auto"],
    },
    {
        "id": "triage-escalate-phishing",
        "agent": "inbox.triage",
        "action": "escalate",
        "effect": "needs_approval",
        "conditions": {"category": "phishing", ">=confidence": 0.95},
        "reason": "Escalate high-confidence phishing for human review",
        "priority": 90,
        "budget": {"cost": 0, "compute": 1, "risk": "low"},
        "enabled": True,
    },
]


@pytest.mark.asyncio
class TestPolicyBundleCRUD:
    """Test policy bundle CRUD operations."""

    async def test_create_bundle_success(self, client: AsyncClient, db: AsyncSession):
        """Test creating a valid policy bundle."""
        response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": VALID_RULES,
                "notes": "Initial policy bundle",
                "created_by": "test@example.com",
                "metadata": {"env": "test"},
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["version"] == "1.0.0"
        assert len(data["rules"]["rules"]) == 2
        assert data["notes"] == "Initial policy bundle"
        assert data["created_by"] == "test@example.com"
        assert data["active"] is False
        assert data["canary_pct"] == 0
        assert data["source"] == "api"

    async def test_create_bundle_duplicate_version(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Test creating bundle with duplicate version fails."""
        # Create first bundle
        await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": VALID_RULES,
                "created_by": "test@example.com",
            },
        )

        # Try to create duplicate
        response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": VALID_RULES,
                "created_by": "test@example.com",
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_create_bundle_invalid_version_format(self, client: AsyncClient):
        """Test creating bundle with invalid version format fails."""
        response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0",  # Invalid: must be X.Y.Z
                "rules": VALID_RULES,
                "created_by": "test@example.com",
            },
        )

        assert response.status_code == 422

    async def test_create_bundle_invalid_rule_schema(self, client: AsyncClient):
        """Test creating bundle with invalid rule schema fails."""
        invalid_rules = [
            {
                "id": "invalid-rule",
                # Missing required fields: agent, action, effect
                "conditions": {},
            }
        ]

        response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": invalid_rules,
                "created_by": "test@example.com",
            },
        )

        assert response.status_code == 422
        assert "validation failed" in str(response.json())

    async def test_create_bundle_duplicate_rule_ids(self, client: AsyncClient):
        """Test creating bundle with duplicate rule IDs fails."""
        duplicate_rules = [
            {
                "id": "same-id",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "First rule",
            },
            {
                "id": "same-id",  # Duplicate!
                "agent": "inbox.triage",
                "action": "escalate",
                "effect": "deny",
                "reason": "Second rule",
            },
        ]

        response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": duplicate_rules,
                "created_by": "test@example.com",
            },
        )

        assert response.status_code == 422
        assert "Duplicate rule IDs" in str(response.json())

    async def test_list_bundles(self, client: AsyncClient, db: AsyncSession):
        """Test listing policy bundles."""
        # Create multiple bundles
        for i in range(3):
            await client.post(
                "/api/policy/bundles",
                json={
                    "version": f"1.{i}.0",
                    "rules": VALID_RULES,
                    "created_by": "test@example.com",
                },
            )

        response = await client.get("/api/policy/bundles")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3
        # Should be ordered by created_at desc
        assert data[0]["version"] == "1.2.0"
        assert data[1]["version"] == "1.1.0"
        assert data[2]["version"] == "1.0.0"

    async def test_get_bundle_by_id(self, client: AsyncClient):
        """Test getting a bundle by ID."""
        # Create bundle
        create_response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": VALID_RULES,
                "created_by": "test@example.com",
            },
        )
        bundle_id = create_response.json()["id"]

        response = await client.get(f"/api/policy/bundles/{bundle_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == bundle_id
        assert data["version"] == "1.0.0"

    async def test_update_bundle(self, client: AsyncClient):
        """Test updating a bundle."""
        # Create bundle
        create_response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": VALID_RULES,
                "created_by": "test@example.com",
            },
        )
        bundle_id = create_response.json()["id"]

        # Update bundle
        updated_rules = VALID_RULES + [
            {
                "id": "new-rule",
                "agent": "knowledge.search",
                "action": "reindex",
                "effect": "needs_approval",
                "reason": "New rule added",
                "budget": {"cost": 10, "risk": "medium"},
            }
        ]

        response = await client.put(
            f"/api/policy/bundles/{bundle_id}",
            json={"rules": updated_rules, "notes": "Updated with new rule"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["rules"]["rules"]) == 3
        assert data["notes"] == "Updated with new rule"

    async def test_delete_bundle(self, client: AsyncClient):
        """Test deleting a bundle."""
        # Create bundle
        create_response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": VALID_RULES,
                "created_by": "test@example.com",
            },
        )
        bundle_id = create_response.json()["id"]

        # Delete bundle
        response = await client.delete(f"/api/policy/bundles/{bundle_id}")

        assert response.status_code == 204

        # Verify deleted
        get_response = await client.get(f"/api/policy/bundles/{bundle_id}")
        assert get_response.status_code == 404

    async def test_diff_bundles(self, client: AsyncClient):
        """Test diffing two policy bundles."""
        # Create bundle v1
        response1 = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": VALID_RULES,
                "created_by": "test@example.com",
            },
        )
        bundle1_id = response1.json()["id"]

        # Create bundle v2 with modifications
        rules_v2 = [
            # Modified rule (different priority)
            {
                **VALID_RULES[0],
                "priority": 85,  # Changed from 80
            },
            # Kept rule
            VALID_RULES[1],
            # New rule
            {
                "id": "new-rule",
                "agent": "knowledge.search",
                "action": "reindex",
                "effect": "allow",
                "reason": "New rule for reindexing",
            },
        ]

        response2 = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.1.0",
                "rules": rules_v2,
                "created_by": "test@example.com",
            },
        )
        bundle2_id = response2.json()["id"]

        # Get diff
        response = await client.get(
            f"/api/policy/bundles/{bundle1_id}/diff/{bundle2_id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["version_a"] == "1.0.0"
        assert data["version_b"] == "1.1.0"
        assert data["summary"]["added"] == 1
        assert data["summary"]["removed"] == 0
        assert data["summary"]["modified"] == 1
        assert data["summary"]["unchanged"] == 1

        assert len(data["rules_added"]) == 1
        assert data["rules_added"][0]["id"] == "new-rule"

        assert len(data["rules_modified"]) == 1
        assert data["rules_modified"][0]["id"] == "triage-quarantine-hi-risk"
