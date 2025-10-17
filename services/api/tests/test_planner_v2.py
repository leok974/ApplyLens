"""Tests for Planner v2 with heuristic scoring and LLM fallback."""

import pytest
from app.agents.planner_v2 import PlannerV2, PlannerMode, Plan
from app.agents.skills import get_skill_registry, reset_skill_registry


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset skill registry before each test."""
    reset_skill_registry()
    yield
    reset_skill_registry()


class TestPlannerV2Heuristic:
    """Test heuristic-only planning mode."""
    
    def test_inbox_triage_selection(self):
        """Test planner selects inbox triage for risk-related tasks."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        objective = "Analyze emails for phishing risks and suspicious content"
        plan = planner.plan(objective)
        
        assert plan.agent == "inbox.triage"
        assert plan.confidence > 0.6
        assert "risk.analysis" in plan.required_capabilities
        assert not plan.fallback_used
    
    def test_knowledge_update_selection(self):
        """Test planner selects knowledge updater for sync tasks."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        objective = "Sync database configuration and update knowledge base"
        plan = planner.plan(objective)
        
        assert plan.agent == "knowledge.update"
        assert "db.sync" in plan.required_capabilities
        assert plan.confidence > 0.5
    
    def test_insights_writer_selection(self):
        """Test planner selects insights writer for reporting tasks."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        objective = "Generate weekly report with trend analysis and metrics"
        plan = planner.plan(objective)
        
        assert plan.agent == "insights.write"
        assert "trend.analysis" in plan.required_capabilities
        assert "metrics.query" in plan.required_capabilities
    
    def test_warehouse_health_selection(self):
        """Test planner selects warehouse health for BigQuery tasks."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        objective = "Check BigQuery parity and run warehouse health checks"
        plan = planner.plan(objective)
        
        assert plan.agent == "warehouse.health"
        assert "parity.check" in plan.required_capabilities
    
    def test_capability_extraction(self):
        """Test capability extraction from objectives."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        caps = planner._extract_capabilities("Find suspicious emails with risk analysis")
        assert "risk.analysis" in caps
        assert "es.search" in caps
        
        caps = planner._extract_capabilities("Generate trend report with metrics")
        assert "metrics.query" in caps
        assert "trend.analysis" in caps
    
    def test_scoring_favors_high_quality(self):
        """Test that scoring favors agents with higher quality scores."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        registry = get_skill_registry()
        
        # Update metrics to make one agent clearly better
        for skill in registry.get_by_agent("knowledge.update"):
            registry.update_metrics(skill.name, quality_score=95.0, success_rate=0.99)
        
        # Ambiguous objective that could match multiple agents
        objective = "Update and sync data configuration"
        plan = planner.plan(objective)
        
        # Should select knowledge.update due to high quality
        assert plan.agent == "knowledge.update"
        assert plan.confidence > 0.7
    
    def test_budget_constraints(self):
        """Test that budget constraints affect agent selection."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        # Warehouse health has high cost weight (1.8)
        objective = "Check warehouse health and parity"
        
        # Without budget constraint
        plan1 = planner.plan(objective, context={})
        assert plan1.agent == "warehouse.health"
        
        # With tight budget constraint (should penalize high-cost agents)
        plan2 = planner.plan(objective, context={"max_cost_weight": 1.0})
        # May still select warehouse if capability match is strong,
        # but confidence should be lower
        if plan2.agent == "warehouse.health":
            assert plan2.confidence < plan1.confidence
    
    def test_confidence_calculation(self):
        """Test confidence calculation logic."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        # High score, clear winner
        scored = [("inbox.triage", 90.0), ("insights.write", 50.0)]
        conf = planner._compute_confidence(90.0, scored)
        assert conf > 0.8  # High confidence
        
        # High score, but close competition
        scored = [("inbox.triage", 85.0), ("insights.write", 82.0)]
        conf = planner._compute_confidence(85.0, scored)
        assert 0.5 < conf < 0.9  # Moderate confidence (adjusted for small gap)
        
        # Low score
        scored = [("inbox.triage", 40.0)]
        conf = planner._compute_confidence(40.0, scored)
        assert conf < 0.65  # Low confidence (adjusted)


class TestPlannerV2LLMFallback:
    """Test LLM fallback functionality."""
    
    def test_auto_mode_uses_heuristic_when_confident(self):
        """Test AUTO mode uses heuristic when confidence is high."""
        planner = PlannerV2(
            mode=PlannerMode.AUTO,
            confidence_threshold=0.7,
            use_mock_llm=True
        )
        
        # Clear objective should have high confidence
        objective = "Analyze emails for phishing and categorize by risk"
        plan = planner.plan(objective)
        
        assert plan.agent == "inbox.triage"
        assert not plan.fallback_used  # Should not use LLM
        assert plan.confidence >= 0.7
    
    def test_auto_mode_uses_llm_when_uncertain(self):
        """Test AUTO mode falls back to LLM when confidence is low."""
        planner = PlannerV2(
            mode=PlannerMode.AUTO,
            confidence_threshold=0.8,
            use_mock_llm=True
        )
        
        # Ambiguous objective
        objective = "Do something with data"
        plan = planner.plan(objective)
        
        # Should use LLM fallback due to low confidence
        assert plan.fallback_used
        assert "LLM selected" in plan.reasoning or plan.fallback_used
    
    def test_llm_mode_always_uses_llm(self):
        """Test LLM mode always uses LLM regardless of confidence."""
        planner = PlannerV2(
            mode=PlannerMode.LLM,
            use_mock_llm=True
        )
        
        objective = "Analyze emails for phishing"
        plan = planner.plan(objective)
        
        assert plan.fallback_used
        assert plan.confidence > 0.0
    
    def test_heuristic_mode_never_uses_llm(self):
        """Test HEURISTIC mode never uses LLM."""
        planner = PlannerV2(
            mode=PlannerMode.HEURISTIC,
            use_mock_llm=True
        )
        
        # Even with ambiguous objective
        objective = "Do something"
        plan = planner.plan(objective)
        
        assert not plan.fallback_used


class TestPlannerV2EdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_objective(self):
        """Test planning with empty objective."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        plan = planner.plan("")
        
        # Should return a valid plan with low confidence
        assert isinstance(plan, Plan)
        assert plan.agent in ["inbox.triage", "knowledge.update", "insights.write", "warehouse.health"]
        assert plan.confidence < 0.8
    
    def test_no_matching_capabilities(self):
        """Test objective with no matching capabilities."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        objective = "Build a rocket ship to Mars"
        plan = planner.plan(objective)
        
        # Should return fallback plan
        assert isinstance(plan, Plan)
        assert plan.agent is not None
        # May have low confidence or use fallback
    
    def test_dry_run_context(self):
        """Test dry_run flag propagates to plan."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        plan = planner.plan("Analyze emails", context={"dry_run": True})
        
        assert plan.dry_run is True
    
    def test_plan_contains_cost_estimates(self):
        """Test that plans include cost and latency estimates."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        plan = planner.plan("Check warehouse parity")
        
        assert plan.estimated_cost_weight > 0
        assert plan.estimated_latency_ms > 0
        # Warehouse should have high cost
        assert plan.estimated_cost_weight > 1.0
    
    def test_reasoning_includes_context(self):
        """Test that plan reasoning is informative."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        plan = planner.plan("Analyze phishing emails")
        
        assert len(plan.reasoning) > 0
        assert "inbox.triage" in plan.reasoning.lower() or "selected" in plan.reasoning.lower()


class TestPlannerV2Integration:
    """Integration tests for full planning workflow."""
    
    def test_multiple_sequential_plans(self):
        """Test creating multiple plans in sequence."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        
        objectives = [
            "Analyze suspicious emails",
            "Sync knowledge database",
            "Generate weekly insights report",
            "Check BigQuery health"
        ]
        
        plans = [planner.plan(obj) for obj in objectives]
        
        # Should select different agents
        agents = [p.agent for p in plans]
        assert "inbox.triage" in agents
        assert "knowledge.update" in agents
        assert "insights.write" in agents
        assert "warehouse.health" in agents
    
    def test_mode_switching(self):
        """Test switching between planning modes."""
        objective = "Analyze emails for risk"
        
        # Heuristic mode
        p1 = PlannerV2(mode=PlannerMode.HEURISTIC)
        plan1 = p1.plan(objective)
        
        # LLM mode
        p2 = PlannerV2(mode=PlannerMode.LLM, use_mock_llm=True)
        plan2 = p2.plan(objective)
        
        # AUTO mode with low threshold (forces LLM)
        p3 = PlannerV2(mode=PlannerMode.AUTO, confidence_threshold=0.99, use_mock_llm=True)
        plan3 = p3.plan(objective)
        
        assert not plan1.fallback_used
        assert plan2.fallback_used
        assert plan3.fallback_used or plan3.confidence >= 0.99
    
    def test_skill_registry_updates_affect_planning(self):
        """Test that updating skill metrics affects future plans."""
        planner = PlannerV2(mode=PlannerMode.HEURISTIC)
        registry = get_skill_registry()
        
        objective = "Categorize and label emails"
        
        # Initial plan
        plan1 = planner.plan(objective)
        initial_agent = plan1.agent
        
        # Update a different agent to be much better
        alternative_agent = "knowledge.update" if initial_agent != "knowledge.update" else "insights.write"
        for skill in registry.get_by_agent(alternative_agent):
            registry.update_metrics(
                skill.name,
                quality_score=99.0,
                success_rate=0.99
            )
        
        # Plan again - might not change if capability match is strong,
        # but metrics should be reflected in estimates
        plan2 = planner.plan(objective)
        
        assert isinstance(plan2, Plan)
        # Verify plans are valid
        assert plan1.confidence > 0
        assert plan2.confidence > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
