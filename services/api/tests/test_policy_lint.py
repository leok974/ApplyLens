# Phase 5.5 PR2: Policy Linter Tests
# Comprehensive tests for policy rule linting

import pytest
from httpx import AsyncClient

from app.policy.lint import lint_rules


# Sample rules for testing
VALID_RULES = [
    {
        "id": "triage-quarantine",
        "agent": "inbox.triage",
        "action": "quarantine",
        "effect": "allow",
        "conditions": {">=risk_score": 90},
        "reason": "Auto-quarantine high-risk emails",
        "priority": 80,
    }
]


@pytest.mark.asyncio
class TestPolicyLinter:
    """Test policy linting logic."""

    def test_valid_rules_no_issues(self):
        """Test that valid rules produce no lint issues."""
        result = lint_rules(VALID_RULES)

        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert not result.has_errors

    def test_duplicate_rule_ids(self):
        """Test detection of duplicate rule IDs."""
        rules = [
            {
                "id": "same-id",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "First rule with same ID",
            },
            {
                "id": "same-id",
                "agent": "inbox.triage",
                "action": "escalate",
                "effect": "deny",
                "reason": "Second rule with same ID",
            },
        ]

        result = lint_rules(rules)

        assert len(result.errors) == 1
        assert "Duplicate rule ID" in result.errors[0].message
        assert result.errors[0].rule_id == "same-id"

    def test_missing_reason(self):
        """Test detection of missing reasons."""
        rules = [
            {
                "id": "no-reason",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                # Missing 'reason' field
            }
        ]

        result = lint_rules(rules)

        assert len(result.errors) == 1
        assert "missing a 'reason'" in result.errors[0].message
        assert result.errors[0].rule_id == "no-reason"

    def test_short_reason_warning(self):
        """Test warning for very short reasons."""
        rules = [
            {
                "id": "short-reason",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "Too short",  # Less than 10 chars
            }
        ]

        result = lint_rules(rules)

        assert len(result.warnings) == 1
        assert "very short reason" in result.warnings[0].message

    def test_conflicting_allow_deny(self):
        """Test detection of conflicting allow/deny rules."""
        rules = [
            {
                "id": "allow-rule",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "Allow quarantine for high risk",
                "priority": 80,
            },
            {
                "id": "deny-rule",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "deny",
                "reason": "Deny quarantine during business hours",
                "priority": 70,
            },
        ]

        result = lint_rules(rules)

        assert len(result.warnings) >= 1
        assert any("Conflicting allow/deny" in w.message for w in result.warnings)

    def test_unreachable_rule(self):
        """Test detection of unreachable rules."""
        rules = [
            {
                "id": "catch-all",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "Allow all quarantine actions",
                "priority": 90,
                # No conditions - catches everything
            },
            {
                "id": "specific-rule",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "Allow quarantine for high risk",
                "priority": 50,
                "conditions": {">=risk_score": 90},
            },
        ]

        result = lint_rules(rules)

        assert len(result.warnings) >= 1
        assert any("unreachable" in w.message.lower() for w in result.warnings)
        assert any(w.rule_id == "specific-rule" for w in result.warnings)

    def test_needs_approval_no_budget(self):
        """Test warning for approval rules without budget."""
        rules = [
            {
                "id": "no-budget-approval",
                "agent": "knowledge.search",
                "action": "reindex",
                "effect": "needs_approval",
                "reason": "Reindex requires approval",
                # Missing 'budget' field
            }
        ]

        result = lint_rules(rules)

        assert len(result.warnings) >= 1
        assert any("no budget" in w.message for w in result.warnings)

    def test_high_cost_budget_warning(self):
        """Test warning for unrealistically high budget costs."""
        rules = [
            {
                "id": "expensive-action",
                "agent": "knowledge.search",
                "action": "reindex",
                "effect": "needs_approval",
                "reason": "Very expensive reindex operation",
                "budget": {
                    "cost": 5000,  # Very high
                    "risk": "high",
                },
            }
        ]

        result = lint_rules(rules)

        assert len(result.warnings) >= 1
        assert any("very high estimated cost" in w.message for w in result.warnings)

    def test_invalid_conditions_type(self):
        """Test error for invalid conditions type."""
        rules = [
            {
                "id": "bad-conditions",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "Rule with invalid conditions",
                "conditions": "not-a-dict",  # Should be dict
            }
        ]

        result = lint_rules(rules)

        assert len(result.errors) >= 1
        assert any("invalid conditions" in e.message for e in result.errors)

    def test_disabled_rule_info(self):
        """Test info message for disabled rules."""
        rules = [
            {
                "id": "disabled-rule",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "Temporarily disabled rule",
                "enabled": False,
            }
        ]

        result = lint_rules(rules)

        assert len(result.info) == 1
        assert "disabled" in result.info[0].message

    def test_multiple_issues(self):
        """Test detection of multiple issues in one ruleset."""
        rules = [
            {
                "id": "dup-id",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "First duplicate",
            },
            {
                "id": "dup-id",  # Duplicate
                "agent": "inbox.triage",
                "action": "escalate",
                "effect": "deny",
                # Missing reason
            },
            {
                "id": "no-budget",
                "agent": "knowledge.search",
                "action": "reindex",
                "effect": "needs_approval",
                "reason": "No budget provided",
                # Missing budget
            },
        ]

        result = lint_rules(rules)

        assert len(result.errors) >= 2  # Duplicate ID + missing reason
        assert len(result.warnings) >= 1  # No budget
        assert result.total_issues >= 3


@pytest.mark.asyncio
class TestPolicyLintEndpoint:
    """Test policy lint REST endpoint."""

    async def test_lint_endpoint_valid(self, client: AsyncClient):
        """Test linting valid rules via endpoint."""
        response = await client.post("/api/policy/lint", json={"rules": VALID_RULES})

        assert response.status_code == 200
        data = response.json()

        assert data["passed"] is True
        assert data["summary"]["errors"] == 0
        assert data["summary"]["total_rules"] == 1

    async def test_lint_endpoint_with_errors(self, client: AsyncClient):
        """Test linting rules with errors."""
        rules_with_errors = [
            {
                "id": "bad-rule",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                # Missing reason
            }
        ]

        response = await client.post(
            "/api/policy/lint", json={"rules": rules_with_errors}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["passed"] is False
        assert data["summary"]["errors"] > 0
        assert len(data["errors"]) > 0
        assert "reason" in data["errors"][0]["message"]

    async def test_lint_endpoint_with_warnings(self, client: AsyncClient):
        """Test linting rules with warnings."""
        rules_with_warnings = [
            {
                "id": "high-cost",
                "agent": "knowledge.search",
                "action": "reindex",
                "effect": "needs_approval",
                "reason": "Expensive reindex operation",
                "budget": {"cost": 2000, "risk": "high"},
            }
        ]

        response = await client.post(
            "/api/policy/lint", json={"rules": rules_with_warnings}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["passed"] is True  # Warnings don't fail the lint
        assert data["summary"]["warnings"] > 0
        assert len(data["warnings"]) > 0

    async def test_lint_endpoint_summary(self, client: AsyncClient):
        """Test that summary includes correct counts."""
        rules = [
            {
                "id": "rule-1",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "Valid rule",
            },
            {
                "id": "rule-2",
                "agent": "inbox.triage",
                "action": "escalate",
                "effect": "allow",
                # Missing reason (error)
            },
            {
                "id": "rule-3",
                "agent": "knowledge.search",
                "action": "reindex",
                "effect": "needs_approval",
                "reason": "Needs budget info",
                # Missing budget (warning)
            },
        ]

        response = await client.post("/api/policy/lint", json={"rules": rules})

        assert response.status_code == 200
        data = response.json()

        summary = data["summary"]
        assert summary["total_rules"] == 3
        assert summary["errors"] >= 1
        assert summary["warnings"] >= 1
        assert (
            summary["total_issues"]
            == summary["errors"] + summary["warnings"] + summary["info"]
        )

    async def test_lint_endpoint_suggestions(self, client: AsyncClient):
        """Test that annotations include helpful suggestions."""
        rules = [
            {
                "id": "dup",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "First rule",
            },
            {
                "id": "dup",
                "agent": "inbox.triage",
                "action": "escalate",
                "effect": "deny",
                "reason": "Second rule",
            },
        ]

        response = await client.post("/api/policy/lint", json={"rules": rules})

        assert response.status_code == 200
        data = response.json()

        # Should have suggestion for duplicate ID
        assert any(e.get("suggestion") is not None for e in data["errors"])
