# Phase 5.5 PR3: Policy Simulation Tests
# Comprehensive tests for what-if policy simulation

import pytest
from httpx import AsyncClient

from app.policy.sim import (
    simulate_rules,
    SimCase,
    generate_fixtures,
    generate_synthetic,
    _rule_matches
)


# Sample rules for testing
SAMPLE_RULES = [
    {
        "id": "quarantine-high-risk",
        "agent": "inbox.triage",
        "action": "quarantine",
        "effect": "allow",
        "conditions": {">=risk_score": 90},
        "reason": "Allow quarantine for high risk",
        "priority": 80
    },
    {
        "id": "deny-low-risk",
        "agent": "inbox.triage",
        "action": "quarantine",
        "effect": "deny",
        "conditions": {"<risk_score": 50},
        "reason": "Deny quarantine for low risk",
        "priority": 70
    },
    {
        "id": "approval-expensive",
        "agent": "knowledge.search",
        "action": "reindex",
        "effect": "needs_approval",
        "conditions": {">=estimated_cost": 100},
        "reason": "Expensive reindex needs approval",
        "priority": 90,
        "budget": {
            "cost": 150,
            "compute": 50,
            "risk": "high"
        }
    }
]


class TestRuleMatching:
    """Test rule matching logic."""
    
    def test_rule_matches_exact(self):
        """Test exact match with conditions."""
        rule = {
            "agent": "inbox.triage",
            "action": "quarantine",
            "conditions": {">=risk_score": 90}
        }
        
        case = SimCase(
            case_id="test_1",
            agent="inbox.triage",
            action="quarantine",
            context={"risk_score": 95}
        )
        
        assert _rule_matches(rule, case) is True
    
    def test_rule_no_match_agent(self):
        """Test no match when agent differs."""
        rule = {
            "agent": "inbox.triage",
            "action": "quarantine",
            "conditions": {}
        }
        
        case = SimCase(
            case_id="test_1",
            agent="knowledge.search",  # Different agent
            action="quarantine",
            context={}
        )
        
        assert _rule_matches(rule, case) is False
    
    def test_rule_no_match_action(self):
        """Test no match when action differs."""
        rule = {
            "agent": "inbox.triage",
            "action": "quarantine",
            "conditions": {}
        }
        
        case = SimCase(
            case_id="test_1",
            agent="inbox.triage",
            action="escalate",  # Different action
            context={}
        )
        
        assert _rule_matches(rule, case) is False
    
    def test_rule_matches_no_conditions(self):
        """Test match when rule has no conditions (catch-all)."""
        rule = {
            "agent": "inbox.triage",
            "action": "quarantine",
            "conditions": {}
        }
        
        case = SimCase(
            case_id="test_1",
            agent="inbox.triage",
            action="quarantine",
            context={"risk_score": 50}
        )
        
        assert _rule_matches(rule, case) is True
    
    def test_rule_no_match_condition_fails(self):
        """Test no match when condition fails."""
        rule = {
            "agent": "inbox.triage",
            "action": "quarantine",
            "conditions": {">=risk_score": 90}
        }
        
        case = SimCase(
            case_id="test_1",
            agent="inbox.triage",
            action="quarantine",
            context={"risk_score": 50}  # Too low
        )
        
        assert _rule_matches(rule, case) is False
    
    def test_rule_operators(self):
        """Test various condition operators."""
        cases_and_expected = [
            ({">=risk_score": 90}, {"risk_score": 90}, True),
            ({">=risk_score": 90}, {"risk_score": 95}, True),
            ({">=risk_score": 90}, {"risk_score": 85}, False),
            ({"<=risk_score": 50}, {"risk_score": 50}, True),
            ({"<=risk_score": 50}, {"risk_score": 30}, True),
            ({"<=risk_score": 50}, {"risk_score": 60}, False),
            ({">risk_score": 90}, {"risk_score": 91}, True),
            ({">risk_score": 90}, {"risk_score": 90}, False),
            ({"<risk_score": 50}, {"risk_score": 49}, True),
            ({"<risk_score": 50}, {"risk_score": 50}, False),
            ({"==category": "phishing"}, {"category": "phishing"}, True),
            ({"==category": "phishing"}, {"category": "spam"}, False),
            ({"!=category": "spam"}, {"category": "phishing"}, True),
            ({"!=category": "spam"}, {"category": "spam"}, False),
        ]
        
        for conditions, context, expected in cases_and_expected:
            rule = {
                "agent": "inbox.triage",
                "action": "quarantine",
                "conditions": conditions
            }
            case = SimCase(
                case_id="test",
                agent="inbox.triage",
                action="quarantine",
                context=context
            )
            assert _rule_matches(rule, case) is expected


class TestSimulation:
    """Test simulation engine."""
    
    def test_simulate_basic(self):
        """Test basic simulation with allow effect."""
        rules = [SAMPLE_RULES[0]]  # quarantine-high-risk
        
        cases = [
            SimCase(
                case_id="high_risk",
                agent="inbox.triage",
                action="quarantine",
                context={"risk_score": 95}
            )
        ]
        
        result = simulate_rules(rules, cases)
        
        assert result.summary.total_cases == 1
        assert result.summary.allow_count == 1
        assert result.summary.allow_rate == 1.0
        assert len(result.results) == 1
        assert result.results[0].effect == "allow"
        assert result.results[0].matched_rule == "quarantine-high-risk"
    
    def test_simulate_deny(self):
        """Test simulation with deny effect."""
        rules = [SAMPLE_RULES[1]]  # deny-low-risk
        
        cases = [
            SimCase(
                case_id="low_risk",
                agent="inbox.triage",
                action="quarantine",
                context={"risk_score": 30}
            )
        ]
        
        result = simulate_rules(rules, cases)
        
        assert result.summary.deny_count == 1
        assert result.summary.deny_rate == 1.0
        assert result.results[0].effect == "deny"
    
    def test_simulate_approval(self):
        """Test simulation with approval effect."""
        rules = [SAMPLE_RULES[2]]  # approval-expensive
        
        cases = [
            SimCase(
                case_id="expensive",
                agent="knowledge.search",
                action="reindex",
                context={"estimated_cost": 150}
            )
        ]
        
        result = simulate_rules(rules, cases)
        
        assert result.summary.approval_count == 1
        assert result.summary.approval_rate == 1.0
        assert result.summary.estimated_cost == 150
        assert result.summary.estimated_compute == 50
        assert result.results[0].effect == "needs_approval"
    
    def test_simulate_no_match(self):
        """Test simulation when no rules match."""
        rules = [SAMPLE_RULES[0]]  # Requires risk_score >= 90
        
        cases = [
            SimCase(
                case_id="low_risk",
                agent="inbox.triage",
                action="quarantine",
                context={"risk_score": 50}  # Doesn't match
            )
        ]
        
        result = simulate_rules(rules, cases)
        
        assert result.summary.no_match_count == 1
        assert result.summary.no_match_rate == 1.0
        assert result.results[0].effect is None
        assert result.results[0].matched_rule is None
    
    def test_simulate_priority_order(self):
        """Test that rules are evaluated by priority."""
        rules = [
            {
                "id": "low-priority",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "deny",
                "reason": "Low priority deny",
                "priority": 50,
                "conditions": {}  # Catch-all
            },
            {
                "id": "high-priority",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "High priority allow",
                "priority": 90,
                "conditions": {">=risk_score": 80}
            }
        ]
        
        cases = [
            SimCase(
                case_id="test",
                agent="inbox.triage",
                action="quarantine",
                context={"risk_score": 85}
            )
        ]
        
        result = simulate_rules(rules, cases)
        
        # Should match high-priority rule first
        assert result.results[0].matched_rule == "high-priority"
        assert result.results[0].effect == "allow"
    
    def test_simulate_disabled_rules(self):
        """Test that disabled rules are not evaluated."""
        rules = [
            {
                "id": "disabled",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "allow",
                "reason": "Disabled rule",
                "priority": 90,
                "enabled": False,  # Disabled
                "conditions": {}
            },
            {
                "id": "enabled",
                "agent": "inbox.triage",
                "action": "quarantine",
                "effect": "deny",
                "reason": "Enabled rule",
                "priority": 50,
                "enabled": True,
                "conditions": {}
            }
        ]
        
        cases = [
            SimCase(
                case_id="test",
                agent="inbox.triage",
                action="quarantine",
                context={}
            )
        ]
        
        result = simulate_rules(rules, cases)
        
        # Should skip disabled rule and match enabled one
        assert result.results[0].matched_rule == "enabled"
        assert result.results[0].effect == "deny"
    
    def test_simulate_budget_breach(self):
        """Test detection of budget breaches."""
        rules = [
            {
                "id": "expensive",
                "agent": "knowledge.search",
                "action": "reindex",
                "effect": "needs_approval",
                "reason": "Expensive operation",
                "priority": 90,
                "conditions": {},
                "budget": {
                    "cost": 600,
                    "compute": 60,
                    "risk": "high"
                }
            }
        ]
        
        # Generate 2 cases that will each cost 600
        cases = [
            SimCase(
                case_id=f"case_{i}",
                agent="knowledge.search",
                action="reindex",
                context={}
            )
            for i in range(2)
        ]
        
        result = simulate_rules(rules, cases)
        
        # Total cost = 1200, should breach $1000 threshold
        assert result.summary.estimated_cost == 1200
        assert len(result.summary.breaches) > 0
        assert any("budget.cost" in b for b in result.summary.breaches)
    
    def test_simulate_mixed_effects(self):
        """Test simulation with mixed effects."""
        cases = [
            SimCase(
                case_id="allow_case",
                agent="inbox.triage",
                action="quarantine",
                context={"risk_score": 95}
            ),
            SimCase(
                case_id="deny_case",
                agent="inbox.triage",
                action="quarantine",
                context={"risk_score": 30}
            ),
            SimCase(
                case_id="approval_case",
                agent="knowledge.search",
                action="reindex",
                context={"estimated_cost": 150}
            )
        ]
        
        result = simulate_rules(SAMPLE_RULES, cases)
        
        assert result.summary.total_cases == 3
        assert result.summary.allow_count == 1
        assert result.summary.deny_count == 1
        assert result.summary.approval_count == 1


class TestFixtures:
    """Test fixture generation."""
    
    def test_generate_fixtures(self):
        """Test that fixtures are generated correctly."""
        fixtures = generate_fixtures()
        
        assert len(fixtures) > 0
        assert all(isinstance(f, SimCase) for f in fixtures)
        assert all(f.case_id for f in fixtures)
        assert all(f.agent for f in fixtures)
        assert all(f.action for f in fixtures)


class TestSynthetic:
    """Test synthetic data generation."""
    
    def test_generate_synthetic(self):
        """Test synthetic case generation."""
        cases = generate_synthetic(count=50, seed=1337)
        
        assert len(cases) == 50
        assert all(isinstance(c, SimCase) for c in cases)
        assert all(c.case_id.startswith("synthetic_") for c in cases)
    
    def test_synthetic_deterministic(self):
        """Test that same seed produces same results."""
        cases1 = generate_synthetic(count=10, seed=42)
        cases2 = generate_synthetic(count=10, seed=42)
        
        assert len(cases1) == len(cases2)
        for c1, c2 in zip(cases1, cases2):
            assert c1.case_id == c2.case_id
            assert c1.agent == c2.agent
            assert c1.action == c2.action
            assert c1.context == c2.context


@pytest.mark.asyncio
class TestSimulationEndpoint:
    """Test simulation REST endpoint."""
    
    async def test_simulate_fixtures(self, client: AsyncClient):
        """Test simulation with fixtures dataset."""
        response = await client.post(
            "/api/policy/simulate",
            json={
                "rules": SAMPLE_RULES,
                "dataset": "fixtures",
                "seed": 1337
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "summary" in data
        assert "results" in data
        assert data["summary"]["total_cases"] > 0
    
    async def test_simulate_synthetic(self, client: AsyncClient):
        """Test simulation with synthetic dataset."""
        response = await client.post(
            "/api/policy/simulate",
            json={
                "rules": SAMPLE_RULES,
                "dataset": "synthetic",
                "synthetic_count": 50,
                "seed": 1337
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["summary"]["total_cases"] == 50
    
    async def test_simulate_custom_cases(self, client: AsyncClient):
        """Test simulation with custom cases."""
        custom_cases = [
            {
                "case_id": "custom_1",
                "agent": "inbox.triage",
                "action": "quarantine",
                "context": {"risk_score": 95}
            }
        ]
        
        response = await client.post(
            "/api/policy/simulate",
            json={
                "rules": SAMPLE_RULES,
                "custom_cases": custom_cases
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["summary"]["total_cases"] == 1
        assert data["results"][0]["case_id"] == "custom_1"
    
    async def test_get_fixtures(self, client: AsyncClient):
        """Test getting fixture cases."""
        response = await client.get("/api/policy/simulate/fixtures")
        
        assert response.status_code == 200
        fixtures = response.json()
        
        assert len(fixtures) > 0
        assert all("case_id" in f for f in fixtures)
    
    async def test_compare_simulations(self, client: AsyncClient):
        """Test comparing two policy bundles."""
        rules_a = [SAMPLE_RULES[0]]  # Only allow rule
        rules_b = [SAMPLE_RULES[1]]  # Only deny rule
        
        response = await client.post(
            "/api/policy/simulate/compare",
            json={
                "rules_a": rules_a,
                "rules_b": rules_b,
                "dataset": "fixtures",
                "seed": 1337
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "summary_a" in data
        assert "summary_b" in data
        assert "deltas" in data
        assert "changes" in data
        assert "total_changes" in data
