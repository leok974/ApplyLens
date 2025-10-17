"""
Tests for Policy Engine - Phase 4 PR1.

Tests policy evaluation, precedence, conditions, and default policies.
"""

import pytest
from app.policy import PolicyEngine, PolicyRule, Budget
from app.policy.defaults import get_default_policies


class TestPolicyEngine:
    """Test PolicyEngine evaluation logic."""
    
    def test_default_allow_no_rules(self):
        """Test default allow when no rules match."""
        engine = PolicyEngine([])
        
        decision = engine.decide(
            agent="test_agent",
            action="test_action",
            context={}
        )
        
        assert decision.effect == "allow"
        assert "default-allow" in decision.reason
        assert decision.rule_id is None
    
    def test_explicit_allow_rule(self):
        """Test explicit allow rule."""
        rules = [
            PolicyRule(
                id="allow-test",
                agent="test_agent",
                action="query",
                effect="allow",
                reason="Read-only queries are allowed"
            )
        ]
        engine = PolicyEngine(rules)
        
        decision = engine.decide(
            agent="test_agent",
            action="query",
            context={}
        )
        
        assert decision.effect == "allow"
        assert decision.rule_id == "allow-test"
        assert "Read-only" in decision.reason
    
    def test_explicit_deny_rule(self):
        """Test explicit deny rule."""
        rules = [
            PolicyRule(
                id="deny-delete",
                agent="test_agent",
                action="delete",
                effect="deny",
                reason="Destructive operations not allowed"
            )
        ]
        engine = PolicyEngine(rules)
        
        decision = engine.decide(
            agent="test_agent",
            action="delete",
            context={}
        )
        
        assert decision.effect == "deny"
        assert decision.rule_id == "deny-delete"
        assert "Destructive" in decision.reason
    
    def test_deny_precedence_over_allow(self):
        """Test that higher-priority rules win regardless of effect."""
        rules = [
            PolicyRule(
                id="low-priority-allow",
                agent="*",
                action="*",
                effect="allow",
                reason="Low priority allow",
                priority=5
            ),
            PolicyRule(
                id="high-priority-deny",
                agent="*",
                action="delete",
                effect="deny",
                reason="High priority deny",
                priority=100
            )
        ]
        engine = PolicyEngine(rules)
        
        decision = engine.decide(
            agent="test_agent",
            action="delete",
            context={}
        )
        
        # High priority deny should win
        assert decision.effect == "deny"
        assert decision.rule_id == "high-priority-deny"
    
    def test_priority_within_effect_type(self):
        """Test that higher priority rules are evaluated first within same effect."""
        rules = [
            PolicyRule(
                id="low-priority-deny",
                agent="*",
                action="test",
                effect="deny",
                reason="Low priority deny",
                priority=10
            ),
            PolicyRule(
                id="high-priority-deny",
                agent="*",
                action="test",
                effect="deny",
                reason="High priority deny",
                priority=100
            )
        ]
        engine = PolicyEngine(rules)
        
        decision = engine.decide(
            agent="test_agent",
            action="test",
            context={}
        )
        
        assert decision.effect == "deny"
        assert decision.rule_id == "high-priority-deny"
    
    def test_wildcard_agent_matching(self):
        """Test wildcard matching for agent."""
        rules = [
            PolicyRule(
                id="global-allow",
                agent="*",
                action="query",
                effect="allow",
                reason="All agents can query"
            )
        ]
        engine = PolicyEngine(rules)
        
        decision = engine.decide(
            agent="any_agent",
            action="query",
            context={}
        )
        
        assert decision.effect == "allow"
        assert decision.rule_id == "global-allow"
    
    def test_wildcard_action_matching(self):
        """Test wildcard matching for action."""
        rules = [
            PolicyRule(
                id="agent-allow-all",
                agent="test_agent",
                action="*",
                effect="allow",
                reason="Agent can do anything"
            )
        ]
        engine = PolicyEngine(rules)
        
        decision = engine.decide(
            agent="test_agent",
            action="any_action",
            context={}
        )
        
        assert decision.effect == "allow"
        assert decision.rule_id == "agent-allow-all"
    
    def test_exact_match_conditions(self):
        """Test exact value matching in conditions."""
        rules = [
            PolicyRule(
                id="env-specific",
                agent="*",
                action="deploy",
                conditions={"environment": "production"},
                effect="deny",
                reason="No production deploys"
            )
        ]
        engine = PolicyEngine(rules)
        
        # Should deny in production
        decision = engine.decide(
            agent="test_agent",
            action="deploy",
            context={"environment": "production"}
        )
        assert decision.effect == "deny"
        
        # Should allow in dev (default)
        decision = engine.decide(
            agent="test_agent",
            action="deploy",
            context={"environment": "development"}
        )
        assert decision.effect == "allow"
    
    def test_numeric_comparison_conditions(self):
        """Test numeric >= comparison in conditions."""
        rules = [
            PolicyRule(
                id="large-changes",
                agent="knowledge_update",
                action="apply",
                conditions={"changes_count": 100},
                effect="deny",
                reason="Large changes need review"
            )
        ]
        engine = PolicyEngine(rules)
        
        # Should deny when >= 100
        decision = engine.decide(
            agent="knowledge_update",
            action="apply",
            context={"changes_count": 150}
        )
        assert decision.effect == "deny"
        
        # Should allow when < 100
        decision = engine.decide(
            agent="knowledge_update",
            action="apply",
            context={"changes_count": 50}
        )
        assert decision.effect == "allow"
    
    def test_multiple_conditions(self):
        """Test rule with multiple conditions (AND logic)."""
        rules = [
            PolicyRule(
                id="complex-rule",
                agent="test_agent",
                action="apply",
                conditions={
                    "environment": "production",
                    "changes_count": 50,
                    "has_review": True
                },
                effect="deny",
                reason="Complex deny condition"
            )
        ]
        engine = PolicyEngine(rules)
        
        # All conditions match - should deny
        decision = engine.decide(
            agent="test_agent",
            action="apply",
            context={
                "environment": "production",
                "changes_count": 100,
                "has_review": True
            }
        )
        assert decision.effect == "deny"
        
        # One condition doesn't match - should allow (default)
        decision = engine.decide(
            agent="test_agent",
            action="apply",
            context={
                "environment": "production",
                "changes_count": 100,
                "has_review": False
            }
        )
        assert decision.effect == "allow"
    
    def test_missing_context_value(self):
        """Test that missing context values cause condition to fail."""
        rules = [
            PolicyRule(
                id="requires-field",
                agent="*",
                action="*",
                conditions={"required_field": "value"},
                effect="deny",
                reason="Field required"
            )
        ]
        engine = PolicyEngine(rules)
        
        # Missing field - rule should not match, default allow
        decision = engine.decide(
            agent="test_agent",
            action="test_action",
            context={}
        )
        assert decision.effect == "allow"
    
    def test_add_rule(self):
        """Test adding rules dynamically."""
        engine = PolicyEngine([])
        
        # Initially allows
        decision = engine.decide("test_agent", "test_action", {})
        assert decision.effect == "allow"
        
        # Add deny rule
        engine.add_rule(PolicyRule(
            id="new-deny",
            agent="test_agent",
            action="test_action",
            effect="deny",
            reason="Added dynamically"
        ))
        
        # Now denies
        decision = engine.decide("test_agent", "test_action", {})
        assert decision.effect == "deny"
    
    def test_remove_rule(self):
        """Test removing rules dynamically."""
        rules = [
            PolicyRule(
                id="removable",
                agent="*",
                action="*",
                effect="deny",
                reason="Will be removed"
            )
        ]
        engine = PolicyEngine(rules)
        
        # Initially denies
        decision = engine.decide("test_agent", "test_action", {})
        assert decision.effect == "deny"
        
        # Remove rule
        removed = engine.remove_rule("removable")
        assert removed is True
        
        # Now allows
        decision = engine.decide("test_agent", "test_action", {})
        assert decision.effect == "allow"
        
        # Try removing non-existent rule
        removed = engine.remove_rule("nonexistent")
        assert removed is False
    
    def test_get_rules(self):
        """Test retrieving rules by agent and action patterns."""
        rules = [
            PolicyRule(id="rule1", agent="agent1", action="action1", effect="allow"),
            PolicyRule(id="rule2", agent="agent1", action="action2", effect="allow"),
            PolicyRule(id="rule3", agent="agent2", action="action1", effect="allow"),
            PolicyRule(id="rule4", agent="*", action="*", effect="allow"),
        ]
        engine = PolicyEngine(rules)
        
        # Get all rules
        all_rules = engine.get_rules()
        assert len(all_rules) == 4
        
        # Get rules for specific agent
        agent1_rules = engine.get_rules(agent="agent1")
        assert len(agent1_rules) == 3  # rule1, rule2, rule4 (wildcard)
        
        # Get rules for specific action
        action1_rules = engine.get_rules(action="action1")
        assert len(action1_rules) == 3  # rule1, rule3, rule4 (wildcard)
        
        # Get rules for specific agent and action
        specific_rules = engine.get_rules(agent="agent1", action="action1")
        assert len(specific_rules) == 2  # rule1, rule4 (wildcard)


class TestBudget:
    """Test Budget schema and checking logic."""
    
    def test_budget_no_limits(self):
        """Test budget with no limits set."""
        budget = Budget()
        
        assert budget.has_limit() is False
        
        result = budget.is_exceeded(elapsed_ms=1000, ops_used=50, cost_cents_used=100)
        assert result["exceeded"] is False
    
    def test_budget_time_limit(self):
        """Test time budget enforcement."""
        budget = Budget(ms=1000)
        
        assert budget.has_limit() is True
        
        # Within budget
        result = budget.is_exceeded(elapsed_ms=500)
        assert result["exceeded"] is False
        assert result["time_limit"] == 1000
        assert result["time_used"] == 500
        
        # Exceeded budget
        result = budget.is_exceeded(elapsed_ms=1500)
        assert result["exceeded"] is True
        assert result["time_exceeded"] is True
    
    def test_budget_ops_limit(self):
        """Test operations budget enforcement."""
        budget = Budget(ops=100)
        
        # Within budget
        result = budget.is_exceeded(ops_used=50)
        assert result["exceeded"] is False
        
        # Exceeded budget
        result = budget.is_exceeded(ops_used=150)
        assert result["exceeded"] is True
        assert result["ops_exceeded"] is True
    
    def test_budget_cost_limit(self):
        """Test cost budget enforcement."""
        budget = Budget(cost_cents=100)
        
        # Within budget
        result = budget.is_exceeded(cost_cents_used=50)
        assert result["exceeded"] is False
        
        # Exceeded budget
        result = budget.is_exceeded(cost_cents_used=150)
        assert result["exceeded"] is True
        assert result["cost_exceeded"] is True
    
    def test_budget_all_limits(self):
        """Test budget with all limits."""
        budget = Budget(ms=1000, ops=100, cost_cents=50)
        
        # All within budget
        result = budget.is_exceeded(elapsed_ms=500, ops_used=50, cost_cents_used=25)
        assert result["exceeded"] is False
        
        # One exceeded
        result = budget.is_exceeded(elapsed_ms=1500, ops_used=50, cost_cents_used=25)
        assert result["exceeded"] is True
        assert result["time_exceeded"] is True
        assert result.get("ops_exceeded") is False
        
        # Multiple exceeded
        result = budget.is_exceeded(elapsed_ms=1500, ops_used=150, cost_cents_used=25)
        assert result["exceeded"] is True
        assert result["time_exceeded"] is True
        assert result["ops_exceeded"] is True


class TestDefaultPolicies:
    """Test default safety policies for Phase 3 agents."""
    
    def test_inbox_triage_auto_quarantine_high_risk(self):
        """Test auto-quarantine for high-risk unknown senders."""
        engine = PolicyEngine(get_default_policies())
        
        # High risk, unknown sender - should allow
        decision = engine.decide(
            agent="inbox_triage",
            action="quarantine",
            context={"risk_score": 95, "sender_known": False}
        )
        assert decision.effect == "allow"
        assert "high-risk" in decision.reason.lower()
    
    def test_inbox_triage_quarantine_requires_approval(self):
        """Test quarantine requires approval for lower risk."""
        engine = PolicyEngine(get_default_policies())
        
        # Lower risk - should deny (require approval)
        decision = engine.decide(
            agent="inbox_triage",
            action="quarantine",
            context={"risk_score": 85, "sender_known": False}
        )
        assert decision.effect == "deny"
        assert decision.requires_approval is True
    
    def test_inbox_triage_allow_labeling(self):
        """Test labeling is always allowed."""
        engine = PolicyEngine(get_default_policies())
        
        decision = engine.decide(
            agent="inbox_triage",
            action="label",
            context={}
        )
        assert decision.effect == "allow"
    
    def test_knowledge_update_deny_large_changes(self):
        """Test denial of large synonym changes."""
        engine = PolicyEngine(get_default_policies())
        
        decision = engine.decide(
            agent="knowledge_update",
            action="apply",
            context={"changes_count": 250, "config_type": "synonyms"}
        )
        assert decision.effect == "deny"
        assert "200" in decision.reason
    
    def test_knowledge_update_deny_regex_rules(self):
        """Test denial of regex routing rules."""
        engine = PolicyEngine(get_default_policies())
        
        decision = engine.decide(
            agent="knowledge_update",
            action="apply",
            context={"config_type": "routing_rules", "has_regex": True}
        )
        assert decision.effect == "deny"
        assert "regex" in decision.reason.lower()
    
    def test_knowledge_update_deny_business_hours(self):
        """Test denial during business hours in production."""
        engine = PolicyEngine(get_default_policies())
        
        decision = engine.decide(
            agent="knowledge_update",
            action="apply",
            context={"environment": "production", "during_business_hours": True}
        )
        assert decision.effect == "deny"
        assert "business hours" in decision.reason.lower()
    
    def test_insights_writer_deny_low_volume(self):
        """Test denial for low volume weeks."""
        engine = PolicyEngine(get_default_policies())
        
        # Agent detects low volume and sets flag
        decision = engine.decide(
            agent="insights_writer",
            action="generate",
            context={"volume_sufficient": False}
        )
        assert decision.effect == "deny"
        assert "low volume" in decision.reason.lower() or "insufficient" in decision.reason.lower()
    
    def test_warehouse_health_allow_dbt_maintenance(self):
        """Test dbt runs allowed during maintenance."""
        engine = PolicyEngine(get_default_policies())
        
        decision = engine.decide(
            agent="warehouse_health",
            action="dbt_run",
            context={"window": "maintenance"}
        )
        assert decision.effect == "allow"
        assert "maintenance" in decision.reason.lower()
    
    def test_warehouse_health_deny_dbt_prod(self):
        """Test dbt runs denied in production outside maintenance."""
        engine = PolicyEngine(get_default_policies())
        
        decision = engine.decide(
            agent="warehouse_health",
            action="dbt_run",
            context={"environment": "production"}
        )
        assert decision.effect == "deny"
    
    def test_global_allow_read_only(self):
        """Test read-only operations always allowed."""
        engine = PolicyEngine(get_default_policies())
        
        for action in ["query", "fetch", "read", "list", "search"]:
            decision = engine.decide(
                agent="any_agent",
                action=action,
                context={}
            )
            assert decision.effect == "allow", f"{action} should be allowed"
    
    def test_global_deny_destructive(self):
        """Test destructive operations always denied."""
        engine = PolicyEngine(get_default_policies())
        
        for action in ["delete", "purge", "drop"]:
            decision = engine.decide(
                agent="any_agent",
                action=action,
                context={}
            )
            assert decision.effect == "deny", f"{action} should be denied"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
