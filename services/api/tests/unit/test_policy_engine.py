"""
Unit Tests for Policy Engine

Tests the JSON-based policy evaluation system including operators,
conditional logic (all/any), and action proposal generation.
"""

from app.logic.policy_engine import apply_policies, _eval_clause, _eval_cond, _get


class TestPolicyEngineBasics:
    """Test basic policy engine functionality."""

    def test_get_nested_field(self):
        """Test nested field access with dot notation."""
        obj = {"features": {"spam_score": 0.8}, "category": "promotions"}
        assert _get("category", obj) == "promotions"
        assert _get("features.spam_score", obj) == 0.8
        assert _get("missing.field", obj) is None

    def test_eval_clause_equals(self):
        """Test equality operator."""
        clause = {"field": "category", "op": "=", "value": "promotions"}
        obj = {"category": "promotions"}
        assert _eval_clause(clause, obj) is True

        obj = {"category": "bills"}
        assert _eval_clause(clause, obj) is False

    def test_eval_clause_comparison(self):
        """Test comparison operators."""
        obj = {"risk_score": 85.0}

        assert (
            _eval_clause({"field": "risk_score", "op": ">", "value": 80}, obj) is True
        )
        assert (
            _eval_clause({"field": "risk_score", "op": ">=", "value": 85}, obj) is True
        )
        assert (
            _eval_clause({"field": "risk_score", "op": "<", "value": 90}, obj) is True
        )
        assert (
            _eval_clause({"field": "risk_score", "op": "<=", "value": 85}, obj) is True
        )
        assert (
            _eval_clause({"field": "risk_score", "op": ">", "value": 90}, obj) is False
        )

    def test_eval_clause_contains(self):
        """Test contains operator."""
        obj = {"subject": "Special offer for you"}
        assert (
            _eval_clause({"field": "subject", "op": "contains", "value": "offer"}, obj)
            is True
        )
        assert (
            _eval_clause(
                {"field": "subject", "op": "contains", "value": "missing"}, obj
            )
            is False
        )

    def test_eval_clause_in(self):
        """Test in operator."""
        obj = {"tags": ["urgent", "action-required"]}
        assert (
            _eval_clause({"field": "tags", "op": "in", "value": ["urgent", "foo"]}, obj)
            is True
        )
        assert (
            _eval_clause({"field": "tags", "op": "in", "value": ["missing"]}, obj)
            is False
        )

    def test_eval_clause_regex(self):
        """Test regex operator."""
        obj = {"subject": "Account verification required"}
        assert (
            _eval_clause(
                {"field": "subject", "op": "regex", "value": r"verif|confirm"}, obj
            )
            is True
        )
        assert (
            _eval_clause({"field": "subject", "op": "regex", "value": r"^urgent"}, obj)
            is False
        )


class TestConditionalLogic:
    """Test all/any conditional logic."""

    def test_eval_cond_all(self):
        """Test 'all' (AND) logic."""
        obj = {"category": "promotions", "risk_score": 30}
        cond = {
            "all": [
                {"field": "category", "op": "=", "value": "promotions"},
                {"field": "risk_score", "op": "<", "value": 50},
            ]
        }
        assert _eval_cond(cond, obj) is True

        # Fail if one condition is false
        obj["risk_score"] = 60
        assert _eval_cond(cond, obj) is False

    def test_eval_cond_any(self):
        """Test 'any' (OR) logic."""
        obj = {"category": "promotions", "risk_score": 30}
        cond = {
            "any": [
                {"field": "category", "op": "=", "value": "bills"},
                {"field": "risk_score", "op": "<", "value": 50},
            ]
        }
        assert _eval_cond(cond, obj) is True

        # Pass if at least one condition is true
        obj["risk_score"] = 60
        obj["category"] = "bills"
        assert _eval_cond(cond, obj) is True

        # Fail if all conditions are false
        obj["category"] = "personal"
        assert _eval_cond(cond, obj) is False

    def test_eval_cond_nested(self):
        """Test nested all/any logic."""
        obj = {"category": "promotions", "risk_score": 30, "has_unsubscribe": True}
        cond = {
            "all": [
                {"field": "category", "op": "=", "value": "promotions"},
                {
                    "any": [
                        {"field": "risk_score", "op": ">", "value": 80},
                        {"field": "has_unsubscribe", "op": "=", "value": True},
                    ]
                },
            ]
        }
        assert _eval_cond(cond, obj) is True


class TestPolicyMatching:
    """Test complete policy matching and action generation."""

    def test_policy_matches_expired_promo(self):
        """Test policy that archives expired promotional emails."""
        email = {
            "id": "x1",
            "category": "promotions",
            "expires_at": "2025-10-01T00:00:00Z",
        }

        policies = [
            {
                "id": "p1",
                "if": {
                    "all": [
                        {"field": "category", "op": "=", "value": "promotions"},
                        {"field": "expires_at", "op": "<", "value": "now"},
                    ]
                },
                "then": {
                    "action": "archive",
                    "confidence_min": 0.75,
                    "rationale": "expired",
                },
            }
        ]

        actions = apply_policies(email, policies, now_iso="2025-10-02T00:00:00Z")

        assert len(actions) == 1
        assert actions[0].action == "archive"
        assert actions[0].confidence >= 0.75
        assert actions[0].policy_id == "p1"
        assert actions[0].email_id == "x1"
        assert actions[0].rationale == "expired"

    def test_policy_no_match(self):
        """Test that policy doesn't match when conditions fail."""
        email = {
            "id": "x1",
            "category": "bills",  # Not promotions
            "expires_at": "2025-10-01T00:00:00Z",
        }

        policies = [
            {
                "id": "p1",
                "if": {
                    "all": [
                        {"field": "category", "op": "=", "value": "promotions"},
                        {"field": "expires_at", "op": "<", "value": "now"},
                    ]
                },
                "then": {
                    "action": "archive",
                    "confidence_min": 0.75,
                    "rationale": "expired",
                },
            }
        ]

        actions = apply_policies(email, policies, now_iso="2025-10-02T00:00:00Z")

        assert len(actions) == 0

    def test_multiple_policies(self):
        """Test that multiple policies can match the same email."""
        email = {
            "id": "x1",
            "category": "promotions",
            "risk_score": 85,
            "expires_at": "2025-10-01T00:00:00Z",
        }

        policies = [
            {
                "id": "expired-promo",
                "if": {
                    "all": [
                        {"field": "category", "op": "=", "value": "promotions"},
                        {"field": "expires_at", "op": "<", "value": "now"},
                    ]
                },
                "then": {
                    "action": "archive",
                    "confidence_min": 0.8,
                    "rationale": "expired",
                },
            },
            {
                "id": "high-risk",
                "if": {"field": "risk_score", "op": ">=", "value": 80},
                "then": {
                    "action": "quarantine",
                    "confidence_min": 0.9,
                    "rationale": "high risk",
                },
            },
        ]

        actions = apply_policies(email, policies, now_iso="2025-10-02T00:00:00Z")

        assert len(actions) == 2
        assert actions[0].action == "archive"
        assert actions[1].action == "quarantine"

    def test_now_placeholder_resolution(self):
        """Test that 'now' placeholder is resolved correctly."""
        email = {
            "id": "x1",
            "category": "promotions",
            "expires_at": "2025-10-01T00:00:00Z",
        }

        policies = [
            {
                "id": "p1",
                "if": {"field": "expires_at", "op": "<", "value": "now"},
                "then": {"action": "archive", "confidence_min": 0.8},
            }
        ]

        # Email expired (now is after expires_at)
        actions = apply_policies(email, policies, now_iso="2025-10-02T00:00:00Z")
        assert len(actions) == 1

        # Email not expired (now is before expires_at)
        actions = apply_policies(email, policies, now_iso="2025-09-30T00:00:00Z")
        assert len(actions) == 0

    def test_action_params(self):
        """Test that action parameters are included in proposed action."""
        email = {"id": "x1", "category": "promotions"}

        policies = [
            {
                "id": "p1",
                "if": {"field": "category", "op": "=", "value": "promotions"},
                "then": {
                    "action": "label",
                    "confidence_min": 0.7,
                    "rationale": "promotional",
                    "params": {"label": "Promotions", "color": "blue"},
                },
            }
        ]

        actions = apply_policies(email, policies)

        assert len(actions) == 1
        assert actions[0].params == {"label": "Promotions", "color": "blue"}

    def test_confidence_minimum(self):
        """Test that confidence is at least 0.5."""
        email = {"id": "x1", "category": "promotions"}

        # Policy with very low confidence_min
        policies = [
            {
                "id": "p1",
                "if": {"field": "category", "op": "=", "value": "promotions"},
                "then": {"action": "archive", "confidence_min": 0.2},
            }
        ]

        actions = apply_policies(email, policies)

        assert len(actions) == 1
        assert actions[0].confidence >= 0.5  # Should be raised to minimum 0.5
