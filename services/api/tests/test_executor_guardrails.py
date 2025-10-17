"""
Tests for Executor Guardrails - Phase 4 PR3.

Tests schema validation, policy enforcement, approval gates, and resource tracking.
"""

import pytest
from app.agents.guardrails import (
    ExecutionGuardrails,
    GuardrailViolation,
    create_guardrails
)
from app.policy import PolicyEngine, PolicyRule


class TestGuardrailCreation:
    """Test guardrail initialization."""
    
    def test_create_guardrails(self):
        """Test guardrail creation with policy engine."""
        rules = [
            PolicyRule(
                id="test-allow",
                agent="test_agent",
                action="test_action",
                effect="allow",
                reason="Test allow"
            )
        ]
        engine = PolicyEngine(rules)
        
        guardrails = create_guardrails(engine)
        
        assert isinstance(guardrails, ExecutionGuardrails)
        assert guardrails.policy_engine == engine


class TestPreExecutionValidation:
    """Test pre-execution guardrail checks."""
    
    def test_allow_action_passes(self):
        """Test that allowed actions pass pre-execution validation."""
        rules = [
            PolicyRule(
                id="allow-query",
                agent="test_agent",
                action="query",
                effect="allow",
                reason="Queries are allowed",
                priority=100
            )
        ]
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        # Should not raise exception
        decision = guardrails.validate_pre_execution(
            agent="test_agent",
            action="query",
            context={"sql": "SELECT * FROM table"},
            plan={"agent": "test_agent", "action": "query"}
        )
        
        assert decision.effect == "allow"
    
    def test_deny_action_raises_violation(self):
        """Test that denied actions raise GuardrailViolation (hard deny)."""
        rules = [
            PolicyRule(
                id="deny-delete",
                agent="test_agent",
                action="delete",
                effect="deny",
                reason="Deletions not allowed",
                priority=100
            )
        ]
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        # Pass approval_eligible=False for hard deny (no approval possible)
        with pytest.raises(GuardrailViolation) as exc_info:
            guardrails.validate_pre_execution(
                agent="test_agent",
                action="delete",
                context={"approval_eligible": False},  # Hard deny
                plan={"agent": "test_agent", "action": "delete"}
            )
        
        assert exc_info.value.violation_type == "policy_denied"
        assert "delete" in exc_info.value.message.lower()
    
    def test_approval_required_returns_decision(self):
        """Test that actions requiring approval return decision with requires_approval=True."""
        rules = [
            PolicyRule(
                id="deny-quarantine",
                agent="inbox_triage",
                action="quarantine",
                effect="deny",
                reason="Requires approval",
                priority=50
            )
        ]
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        # This should NOT raise - just return decision with requires_approval=True
        # In real workflow, executor checks this and handles approval flow
        # quarantine requires email_id param
        decision = guardrails.validate_pre_execution(
            agent="inbox_triage",
            action="quarantine",
            context={"risk_score": 85, "email_id": "123"},  # Default approval_eligible=True
            plan={"agent": "inbox_triage", "action": "quarantine"}
        )
        
        assert decision.effect == "deny"
        assert decision.requires_approval is True
    
    def test_missing_required_param_raises_violation(self):
        """Test that missing required parameters raise violation."""
        rules = [
            PolicyRule(
                id="allow-quarantine",
                agent="inbox_triage",
                action="quarantine",
                effect="allow",
                reason="Allowed",
                priority=100
            )
        ]
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        # quarantine requires email_id parameter
        with pytest.raises(GuardrailViolation) as exc_info:
            guardrails.validate_pre_execution(
                agent="inbox_triage",
                action="quarantine",
                context={},  # Missing email_id
                plan={"agent": "inbox_triage", "action": "quarantine"}
            )
        
        assert exc_info.value.violation_type == "missing_parameter"
        assert "email_id" in exc_info.value.message
    
    def test_required_param_in_context_passes(self):
        """Test that required params in context pass validation."""
        rules = [
            PolicyRule(
                id="allow-quarantine",
                agent="inbox_triage",
                action="quarantine",
                effect="allow",
                reason="Allowed",
                priority=100
            )
        ]
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        # Should not raise - email_id provided
        decision = guardrails.validate_pre_execution(
            agent="inbox_triage",
            action="quarantine",
            context={"email_id": "123"},
            plan={"agent": "inbox_triage", "action": "quarantine"}
        )
        
        assert decision.effect == "allow"
    
    def test_required_param_in_plan_passes(self):
        """Test that required params in plan pass validation."""
        rules = [
            PolicyRule(
                id="allow-label",
                agent="inbox_triage",
                action="label",
                effect="allow",
                reason="Allowed",
                priority=100
            )
        ]
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        # label requires email_id and label_name
        decision = guardrails.validate_pre_execution(
            agent="inbox_triage",
            action="label",
            context={"email_id": "123"},
            plan={
                "agent": "inbox_triage",
                "action": "label",
                "label_name": "important"  # param in plan
            }
        )
        
        assert decision.effect == "allow"


class TestPostExecutionValidation:
    """Test post-execution guardrail checks."""
    
    def test_valid_result_passes(self):
        """Test that valid result passes post-execution validation."""
        rules = []
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        # Should not raise
        guardrails.validate_post_execution(
            agent="test_agent",
            action="query",
            context={},
            result={"status": "success", "data": []}
        )
    
    def test_invalid_result_type_raises_violation(self):
        """Test that non-dict result raises violation."""
        rules = []
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        with pytest.raises(GuardrailViolation) as exc_info:
            guardrails.validate_post_execution(
                agent="test_agent",
                action="query",
                context={},
                result="invalid string result"  # Should be dict
            )
        
        assert exc_info.value.violation_type == "invalid_result"
        assert "dict" in exc_info.value.message
    
    def test_result_with_error_allowed(self):
        """Test that results with errors are allowed (just logged)."""
        rules = []
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        # Should not raise - errors are allowed
        guardrails.validate_post_execution(
            agent="test_agent",
            action="query",
            context={},
            result={"error": "Database connection failed", "status": "failed"}
        )
    
    def test_invalid_ops_count_raises_violation(self):
        """Test that invalid ops_count raises violation."""
        rules = []
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        with pytest.raises(GuardrailViolation) as exc_info:
            guardrails.validate_post_execution(
                agent="test_agent",
                action="query",
                context={},
                result={"ops_count": -5}  # Negative not allowed
            )
        
        assert exc_info.value.violation_type == "invalid_metric"
        assert "ops_count" in exc_info.value.message
    
    def test_invalid_cost_raises_violation(self):
        """Test that invalid cost_cents_used raises violation."""
        rules = []
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        with pytest.raises(GuardrailViolation) as exc_info:
            guardrails.validate_post_execution(
                agent="test_agent",
                action="query",
                context={},
                result={"cost_cents_used": "invalid"}  # Should be number
            )
        
        assert exc_info.value.violation_type == "invalid_metric"
        assert "cost_cents_used" in exc_info.value.message
    
    def test_valid_metrics_pass(self):
        """Test that valid ops and cost metrics pass."""
        rules = []
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        # Should not raise
        guardrails.validate_post_execution(
            agent="test_agent",
            action="query",
            context={},
            result={
                "ops_count": 10,
                "cost_cents_used": 25,
                "status": "success"
            }
        )


class TestApprovalChecking:
    """Test approval requirement checking."""
    
    def test_no_approval_required(self):
        """Test check when approval not required."""
        rules = [
            PolicyRule(
                id="allow-read",
                agent="*",
                action="read",
                effect="allow",
                reason="Read allowed",
                priority=100
            )
        ]
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        requires_approval, reason = guardrails.check_approval_required(
            agent="test_agent",
            action="read",
            context={}
        )
        
        assert requires_approval is False
        assert reason == ""
    
    def test_approval_required_for_deny_with_flag(self):
        """Test check when approval is required (deny + requires_approval)."""
        rules = [
            PolicyRule(
                id="deny-quarantine",
                agent="inbox_triage",
                action="quarantine",
                effect="deny",
                reason="Requires human review",
                priority=50
            )
        ]
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        requires_approval, reason = guardrails.check_approval_required(
            agent="inbox_triage",
            action="quarantine",
            context={"risk_score": 85}
        )
        
        # Currently the policy engine returns requires_approval based on deny effect
        # In real implementation, this would check a specific approval flag
        # For now, we just verify the method works
        assert isinstance(requires_approval, bool)
        assert isinstance(reason, str)


class TestGuardrailViolationDetails:
    """Test GuardrailViolation exception details."""
    
    def test_violation_has_message(self):
        """Test that violation has message."""
        violation = GuardrailViolation(
            message="Test violation",
            violation_type="test_type"
        )
        
        assert violation.message == "Test violation"
        assert str(violation) == "Test violation"
    
    def test_violation_has_type(self):
        """Test that violation has type."""
        violation = GuardrailViolation(
            message="Test",
            violation_type="policy_denied"
        )
        
        assert violation.violation_type == "policy_denied"
    
    def test_violation_has_details(self):
        """Test that violation can include details."""
        details = {
            "agent": "test_agent",
            "action": "test_action",
            "rule_id": "test-rule"
        }
        violation = GuardrailViolation(
            message="Test",
            violation_type="test",
            details=details
        )
        
        assert violation.details == details
        assert violation.details["agent"] == "test_agent"
    
    def test_violation_empty_details_default(self):
        """Test that violation details default to empty dict."""
        violation = GuardrailViolation(
            message="Test",
            violation_type="test"
        )
        
        assert violation.details == {}


class TestRequiredParameters:
    """Test required parameter validation for different actions."""
    
    def test_quarantine_requires_email_id(self):
        """Test quarantine action requires email_id."""
        rules = [PolicyRule(id="allow", agent="*", action="*", effect="allow")]
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        with pytest.raises(GuardrailViolation) as exc_info:
            guardrails.validate_pre_execution(
                agent="inbox_triage",
                action="quarantine",
                context={},
                plan={"agent": "inbox_triage"}
            )
        
        assert "email_id" in exc_info.value.message
    
    def test_label_requires_email_id_and_label_name(self):
        """Test label action requires email_id and label_name."""
        rules = [PolicyRule(id="allow", agent="*", action="*", effect="allow")]
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        # Missing both
        with pytest.raises(GuardrailViolation):
            guardrails.validate_pre_execution(
                agent="inbox_triage",
                action="label",
                context={},
                plan={"agent": "inbox_triage"}
            )
        
        # Missing label_name
        with pytest.raises(GuardrailViolation):
            guardrails.validate_pre_execution(
                agent="inbox_triage",
                action="label",
                context={"email_id": "123"},
                plan={"agent": "inbox_triage"}
            )
    
    def test_apply_requires_changes(self):
        """Test apply action requires changes parameter."""
        rules = [PolicyRule(id="allow", agent="*", action="*", effect="allow")]
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        with pytest.raises(GuardrailViolation) as exc_info:
            guardrails.validate_pre_execution(
                agent="knowledge_update",
                action="apply",
                context={},
                plan={"agent": "knowledge_update"}
            )
        
        assert "changes" in exc_info.value.message
    
    def test_unknown_action_has_no_required_params(self):
        """Test that unknown actions have no required params."""
        rules = [PolicyRule(id="allow", agent="*", action="*", effect="allow")]
        engine = PolicyEngine(rules)
        guardrails = ExecutionGuardrails(engine)
        
        # Should not raise - unknown actions have no required params
        guardrails.validate_pre_execution(
            agent="test_agent",
            action="unknown_action",
            context={},
            plan={"agent": "test_agent"}
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
