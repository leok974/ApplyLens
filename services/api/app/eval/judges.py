"""
Mock judges for deterministic CI testing.

These judges use heuristics to score agent outputs without LLM calls.
For production, real LLM-based judges can be swapped in.
"""
from typing import Dict, Any, List
from .models import Judge, EvalTask, Invariant


class RiskAccuracyJudge(Judge):
    """Judge for inbox.triage risk scoring accuracy."""
    
    def __init__(self):
        super().__init__(
            name="risk_accuracy_judge",
            agent="inbox.triage",
            categories=["phishing_detection", "risk_scoring", "categorization"],
            use_llm=False,
        )
    
    def score(self, task: EvalTask, output: Dict[str, Any]) -> tuple[float, str]:
        """Score based on risk level and phishing detection accuracy."""
        expected = task.expected_output or {}
        
        score = 0.0
        reasons = []
        
        # Check risk level (40 points)
        expected_risk = expected.get("risk_level", "medium")
        actual_risk = output.get("risk_level", "medium")
        
        risk_values = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        expected_val = risk_values.get(expected_risk, 2)
        actual_val = risk_values.get(actual_risk, 2)
        diff = abs(expected_val - actual_val)
        
        if diff == 0:
            score += 40
            reasons.append("Risk level exact match")
        elif diff == 1:
            score += 25
            reasons.append("Risk level close (off by 1)")
        else:
            score += 10
            reasons.append(f"Risk level mismatch: expected {expected_risk}, got {actual_risk}")
        
        # Check phishing flag (40 points)
        expected_phishing = expected.get("is_phishing", False)
        actual_phishing = output.get("is_phishing", False)
        
        if expected_phishing == actual_phishing:
            score += 40
            reasons.append("Phishing detection correct")
        else:
            reasons.append(f"Phishing detection wrong: expected {expected_phishing}, got {actual_phishing}")
        
        # Check category (20 points)
        expected_category = expected.get("category")
        actual_category = output.get("category")
        
        if expected_category and actual_category == expected_category:
            score += 20
            reasons.append("Category correct")
        elif expected_category and actual_category:
            score += 10
            reasons.append(f"Category wrong: expected {expected_category}, got {actual_category}")
        else:
            score += 10
            reasons.append("Category not provided or not expected")
        
        reasoning = "; ".join(reasons)
        return score, reasoning


class SyncAccuracyJudge(Judge):
    """Judge for knowledge.update sync accuracy."""
    
    def __init__(self):
        super().__init__(
            name="sync_accuracy_judge",
            agent="knowledge.update",
            categories=["sync", "update"],
            use_llm=False,
        )
    
    def score(self, task: EvalTask, output: Dict[str, Any]) -> tuple[float, str]:
        """Score based on sync accuracy and synonym preservation."""
        expected = task.expected_output or {}
        
        score = 0.0
        reasons = []
        
        # Check items synced (50 points)
        expected_synced = expected.get("items_synced", 0)
        actual_synced = output.get("items_synced", 0)
        
        if actual_synced == expected_synced:
            score += 50
            reasons.append(f"Correct items synced: {actual_synced}")
        elif actual_synced > 0:
            # Partial credit
            ratio = min(actual_synced / max(expected_synced, 1), 1.0)
            score += 50 * ratio
            reasons.append(f"Partial sync: {actual_synced}/{expected_synced}")
        else:
            reasons.append("No items synced")
        
        # Check synonym preservation (30 points)
        expected_synonyms = expected.get("synonyms_preserved", True)
        actual_synonyms = output.get("synonyms_preserved", True)
        
        if actual_synonyms == expected_synonyms:
            score += 30
            reasons.append("Synonyms preserved correctly")
        else:
            reasons.append(f"Synonym preservation issue: expected {expected_synonyms}, got {actual_synonyms}")
        
        # Check conflicts (20 points)
        expected_conflicts = expected.get("conflicts_resolved", 0)
        actual_conflicts = output.get("conflicts_resolved", 0)
        
        if actual_conflicts == expected_conflicts:
            score += 20
            reasons.append(f"Conflicts resolved: {actual_conflicts}")
        elif actual_conflicts >= 0:
            score += 10
            reasons.append(f"Conflict resolution partial: {actual_conflicts}/{expected_conflicts}")
        
        reasoning = "; ".join(reasons)
        return score, reasoning


class InsightsQualityJudge(Judge):
    """Judge for insights.write report quality."""
    
    def __init__(self):
        super().__init__(
            name="insights_quality_judge",
            agent="insights.write",
            categories=["analysis", "report"],
            use_llm=False,
        )
    
    def score(self, task: EvalTask, output: Dict[str, Any]) -> tuple[float, str]:
        """Score based on insight quality, metrics, and clarity."""
        expected = task.expected_output or {}
        
        score = 0.0
        reasons = []
        
        # Check metrics found (40 points)
        expected_metrics = expected.get("metrics_count", 0)
        actual_metrics = output.get("metrics_count", 0)
        
        if actual_metrics >= expected_metrics:
            score += 40
            reasons.append(f"Sufficient metrics: {actual_metrics}")
        elif actual_metrics > 0:
            ratio = actual_metrics / max(expected_metrics, 1)
            score += 40 * ratio
            reasons.append(f"Some metrics: {actual_metrics}/{expected_metrics}")
        else:
            reasons.append("No metrics found")
        
        # Check trends identified (30 points)
        expected_trends = expected.get("trends", [])
        actual_trends = output.get("trends", [])
        
        if len(actual_trends) >= len(expected_trends):
            score += 30
            reasons.append(f"Trends identified: {len(actual_trends)}")
        elif actual_trends:
            score += 15
            reasons.append(f"Some trends: {len(actual_trends)}/{len(expected_trends)}")
        else:
            reasons.append("No trends identified")
        
        # Check report structure (30 points)
        has_summary = output.get("has_summary", False)
        has_recommendations = output.get("has_recommendations", False)
        
        if has_summary and has_recommendations:
            score += 30
            reasons.append("Complete report structure")
        elif has_summary or has_recommendations:
            score += 15
            reasons.append("Partial report structure")
        else:
            reasons.append("Missing report structure")
        
        reasoning = "; ".join(reasons)
        return score, reasoning


class WarehouseHealthJudge(Judge):
    """Judge for warehouse.health monitoring."""
    
    def __init__(self):
        super().__init__(
            name="warehouse_health_judge",
            agent="warehouse.health",
            categories=["monitoring", "health_check", "parity"],
            use_llm=False,
        )
    
    def score(self, task: EvalTask, output: Dict[str, Any]) -> tuple[float, str]:
        """Score based on health checks and parity detection."""
        expected = task.expected_output or {}
        
        score = 0.0
        reasons = []
        
        # Check health status (40 points)
        expected_healthy = expected.get("is_healthy", True)
        actual_healthy = output.get("is_healthy", True)
        
        if actual_healthy == expected_healthy:
            score += 40
            reasons.append(f"Health status correct: {actual_healthy}")
        else:
            reasons.append(f"Health status wrong: expected {expected_healthy}, got {actual_healthy}")
        
        # Check issues detected (40 points)
        expected_issues = expected.get("issues_count", 0)
        actual_issues = output.get("issues_count", 0)
        
        if actual_issues == expected_issues:
            score += 40
            reasons.append(f"Issues detected correctly: {actual_issues}")
        elif actual_issues >= 0:
            # Allow some tolerance
            diff = abs(actual_issues - expected_issues)
            if diff <= 1:
                score += 30
                reasons.append(f"Issues detection close: {actual_issues} vs {expected_issues}")
            else:
                score += 10
                reasons.append(f"Issues detection off: {actual_issues} vs {expected_issues}")
        
        # Check parity (20 points)
        expected_parity = expected.get("parity_ok", True)
        actual_parity = output.get("parity_ok", True)
        
        if actual_parity == expected_parity:
            score += 20
            reasons.append("Parity check correct")
        else:
            reasons.append(f"Parity check wrong: expected {expected_parity}, got {actual_parity}")
        
        reasoning = "; ".join(reasons)
        return score, reasoning


# Registry of available judges
JUDGE_REGISTRY: Dict[str, Judge] = {
    "inbox.triage": RiskAccuracyJudge(),
    "knowledge.update": SyncAccuracyJudge(),
    "insights.write": InsightsQualityJudge(),
    "warehouse.health": WarehouseHealthJudge(),
}


def get_judge(agent: str) -> Judge:
    """Get the appropriate judge for an agent."""
    if agent not in JUDGE_REGISTRY:
        raise ValueError(f"No judge available for agent: {agent}")
    return JUDGE_REGISTRY[agent]


# Invariants

class NoFalseNegativesPhishingInvariant(Invariant):
    """Critical: Never miss obvious phishing."""
    
    def __init__(self):
        super().__init__(
            id="no_false_negatives_phishing",
            name="No False Negatives on Phishing",
            agent="inbox.triage",
            description="Must detect obvious phishing emails (high-risk keywords, suspicious domains)",
            severity="critical",
        )
    
    def check(self, task: EvalTask, output: Dict[str, Any]) -> tuple[bool, str]:
        """Check if obvious phishing was detected."""
        expected = task.expected_output or {}
        
        # Only check if expected output says it's phishing
        expected_phishing = expected.get("is_phishing", False)
        if not expected_phishing:
            return True, "Not a phishing test case"
        
        # Check if agent detected it
        actual_phishing = output.get("is_phishing", False)
        risk_level = output.get("risk_level", "low")
        
        # Must either flag as phishing OR mark as high/critical risk
        if actual_phishing or risk_level in ["high", "critical"]:
            return True, f"Phishing detected: is_phishing={actual_phishing}, risk={risk_level}"
        
        return False, f"False negative: missed phishing (is_phishing={actual_phishing}, risk={risk_level})"


class SyncCompletionInvariant(Invariant):
    """High: Sync must complete without data loss."""
    
    def __init__(self):
        super().__init__(
            id="sync_completion",
            name="Sync Completes Successfully",
            agent="knowledge.update",
            description="Sync operations must complete and sync at least 95% of items",
            severity="high",
        )
    
    def check(self, task: EvalTask, output: Dict[str, Any]) -> tuple[bool, str]:
        """Check if sync completed successfully."""
        expected = task.expected_output or {}
        expected_synced = expected.get("items_synced", 0)
        actual_synced = output.get("items_synced", 0)
        
        if expected_synced == 0:
            return True, "No items expected to sync"
        
        completion_rate = actual_synced / expected_synced
        
        if completion_rate >= 0.95:
            return True, f"Sync completion: {actual_synced}/{expected_synced} ({completion_rate:.1%})"
        
        return False, f"Sync incomplete: {actual_synced}/{expected_synced} ({completion_rate:.1%})"


class InsightsDataQualityInvariant(Invariant):
    """High: Insights must include valid metrics."""
    
    def __init__(self):
        super().__init__(
            id="insights_data_quality",
            name="Insights Include Valid Metrics",
            agent="insights.write",
            description="Reports must include at least 3 valid metrics with proper formatting",
            severity="high",
        )
    
    def check(self, task: EvalTask, output: Dict[str, Any]) -> tuple[bool, str]:
        """Check if insights include valid metrics."""
        metrics_count = output.get("metrics_count", 0)
        
        if metrics_count >= 3:
            return True, f"Valid metrics: {metrics_count}"
        
        return False, f"Insufficient metrics: {metrics_count} (need at least 3)"


class WarehouseParityInvariant(Invariant):
    """Critical: Must detect severe parity issues."""
    
    def __init__(self):
        super().__init__(
            id="warehouse_parity_detection",
            name="Warehouse Parity Detection",
            agent="warehouse.health",
            description="Must detect when data parity is broken (>10% discrepancy)",
            severity="critical",
        )
    
    def check(self, task: EvalTask, output: Dict[str, Any]) -> tuple[bool, str]:
        """Check if parity issues are detected."""
        expected = task.expected_output or {}
        
        # If expected says parity is broken, we must detect it
        expected_parity = expected.get("parity_ok", True)
        if expected_parity:
            return True, "Parity expected to be OK"
        
        # Check if we detected the issue
        actual_parity = output.get("parity_ok", True)
        is_healthy = output.get("is_healthy", True)
        
        if not actual_parity or not is_healthy:
            return True, f"Parity issue detected: parity_ok={actual_parity}, is_healthy={is_healthy}"
        
        return False, f"Failed to detect parity issue: parity_ok={actual_parity}, is_healthy={is_healthy}"


# Invariant registry
INVARIANT_REGISTRY: Dict[str, Invariant] = {
    "no_false_negatives_phishing": NoFalseNegativesPhishingInvariant(),
    "sync_completion": SyncCompletionInvariant(),
    "insights_data_quality": InsightsDataQualityInvariant(),
    "warehouse_parity_detection": WarehouseParityInvariant(),
}


def get_invariant(invariant_id: str) -> Invariant:
    """Get an invariant by ID."""
    if invariant_id not in INVARIANT_REGISTRY:
        raise ValueError(f"Unknown invariant: {invariant_id}")
    return INVARIANT_REGISTRY[invariant_id]
