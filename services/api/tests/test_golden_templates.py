"""
Golden Snapshot Tests for Templates - Phase 5.4 PR6

Validates template rendering produces consistent output.
Golden files stored in tests/golden/ directory.
"""
import pytest
import os
from pathlib import Path

from app.intervene.templates import render_incident_issue
from app.models_incident import Incident


# Golden files directory
GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN_DIR.mkdir(exist_ok=True)


def read_golden(filename: str) -> str:
    """Read golden file content."""
    filepath = GOLDEN_DIR / filename
    if not filepath.exists():
        return None
    return filepath.read_text()


def write_golden(filename: str, content: str):
    """Write golden file content."""
    filepath = GOLDEN_DIR / filename
    filepath.write_text(content)


def compare_or_update_golden(filename: str, actual: str, update: bool = False):
    """
    Compare actual output to golden file.
    
    If update=True, write new golden file.
    If update=False, assert actual matches golden.
    """
    if update or os.getenv("UPDATE_GOLDEN") == "1":
        write_golden(filename, actual)
        pytest.skip(f"Updated golden file: {filename}")
    
    expected = read_golden(filename)
    
    if expected is None:
        # Golden file doesn't exist, create it
        write_golden(filename, actual)
        pytest.skip(f"Created golden file: {filename}")
    
    assert actual == expected, f"Output differs from golden file: {filename}"


class TestInvariantFailureTemplate:
    """Test invariant failure template rendering."""
    
    def test_basic_invariant_failure(self):
        """Test basic invariant failure template."""
        incident = Incident(
            id=1,
            kind="invariant",
            key="INV_data_freshness_inbox",
            severity="sev1",
            status="open",
            summary="Invariant failed: data_freshness for inbox.triage",
            details={
                "invariant": {
                    "id": "data_freshness_inbox",
                    "name": "Data Freshness - Inbox",
                    "description": "Inbox data must be < 5 minutes old",
                    "threshold": 300,
                    "actual": 1800,
                },
                "eval_result": {
                    "id": "eval-123",
                    "agent": "inbox.triage",
                    "task": "triage_emails",
                    "score": 78.5,
                },
            },
        )
        
        output = render_incident_issue(incident, template_type="invariant_failure")
        
        compare_or_update_golden("invariant_failure_basic.md", output)
    
    def test_invariant_with_playbooks(self):
        """Test invariant failure with suggested playbooks."""
        incident = Incident(
            id=2,
            kind="invariant",
            key="INV_quality_threshold_warehouse",
            severity="sev2",
            status="open",
            summary="Invariant failed: quality_threshold for warehouse.health",
            details={
                "invariant": {
                    "id": "quality_threshold_warehouse",
                    "name": "Quality Threshold - Warehouse",
                    "description": "Quality score must be >= 90",
                    "threshold": 90,
                    "actual": 82,
                },
                "eval_result": {
                    "id": "eval-456",
                    "agent": "warehouse.health",
                    "task": "check_dbt_freshness",
                    "score": 82.0,
                },
            },
            playbooks=["rerun_eval", "rerun_dbt", "refresh_dbt_dependencies"],
        )
        
        output = render_incident_issue(incident, template_type="invariant_failure")
        
        compare_or_update_golden("invariant_failure_with_playbooks.md", output)


class TestBudgetExceededTemplate:
    """Test budget exceeded template rendering."""
    
    def test_latency_budget_exceeded(self):
        """Test latency budget violation template."""
        incident = Incident(
            id=3,
            kind="budget",
            key="BUDGET_inbox.triage_latency_p95",
            severity="sev2",
            status="open",
            summary="Budget violation: inbox.triage latency_p95",
            details={
                "violation": {
                    "agent": "inbox.triage",
                    "budget_type": "latency_p95",
                    "threshold": 1000.0,
                    "actual": 1850.0,
                    "severity": "error",
                    "message": "P95 latency 1850ms exceeds budget 1000ms",
                },
                "budget": {
                    "agent": "inbox.triage",
                    "description": "Email triage must be fast and accurate",
                },
                "current_metrics": {
                    "avg_latency_ms": 650.0,
                    "p95_latency_ms": 1850.0,
                    "p99_latency_ms": 2500.0,
                },
            },
            playbooks=["clear_cache", "refresh_synonyms"],
        )
        
        output = render_incident_issue(incident, template_type="budget_exceeded")
        
        compare_or_update_golden("budget_latency_exceeded.md", output)
    
    def test_quality_budget_exceeded(self):
        """Test quality budget violation template."""
        incident = Incident(
            id=4,
            kind="budget",
            key="BUDGET_warehouse.health_quality",
            severity="sev1",
            status="open",
            summary="Budget violation: warehouse.health quality",
            details={
                "violation": {
                    "agent": "warehouse.health",
                    "budget_type": "quality",
                    "threshold": 90.0,
                    "actual": 78.5,
                    "severity": "critical",
                    "message": "Quality score 78.5 below budget 90.0",
                },
                "budget": {
                    "agent": "warehouse.health",
                    "description": "Warehouse health checks must be highly reliable",
                },
                "current_metrics": {
                    "avg_quality_score": 78.5,
                    "success_rate": 0.88,
                },
            },
            playbooks=["rerun_eval", "rerun_dbt"],
        )
        
        output = render_incident_issue(incident, template_type="budget_exceeded")
        
        compare_or_update_golden("budget_quality_exceeded.md", output)


class TestPlannerRegressionTemplate:
    """Test planner regression template rendering."""
    
    def test_accuracy_regression(self):
        """Test planner accuracy regression template."""
        incident = Incident(
            id=5,
            kind="planner",
            key="PLANNER_REG_v1.2.3-canary",
            severity="sev1",
            status="open",
            summary="Planner regression: v1.2.3-canary accuracy",
            details={
                "version": "v1.2.3-canary",
                "regression": {
                    "metric": "accuracy",
                    "threshold": 0.90,
                    "actual": 0.82,
                    "baseline": 0.95,
                    "drop": 0.13,
                },
                "metrics": {
                    "current": {
                        "accuracy": 0.82,
                        "latency_p95": 450,
                        "error_rate": 0.18,
                    },
                    "baseline": {
                        "accuracy": 0.95,
                        "latency_p95": 400,
                        "error_rate": 0.05,
                    },
                },
            },
            playbooks=["rollback_planner", "adjust_canary_split"],
        )
        
        output = render_incident_issue(incident, template_type="planner_regression")
        
        compare_or_update_golden("planner_accuracy_regression.md", output)
    
    def test_latency_regression(self):
        """Test planner latency regression template."""
        incident = Incident(
            id=6,
            kind="planner",
            key="PLANNER_REG_v1.3.0-canary",
            severity="sev2",
            status="open",
            summary="Planner regression: v1.3.0-canary latency_p95",
            details={
                "version": "v1.3.0-canary",
                "regression": {
                    "metric": "latency_p95",
                    "threshold": 520,
                    "actual": 850,
                    "baseline": 400,
                    "increase_pct": 1.125,
                },
                "metrics": {
                    "current": {
                        "accuracy": 0.94,
                        "latency_p95": 850,
                        "error_rate": 0.06,
                    },
                    "baseline": {
                        "accuracy": 0.95,
                        "latency_p95": 400,
                        "error_rate": 0.05,
                    },
                },
            },
            playbooks=["rollback_planner", "adjust_canary_split"],
        )
        
        output = render_incident_issue(incident, template_type="planner_regression")
        
        compare_or_update_golden("planner_latency_regression.md", output)


class TestTemplateConsistency:
    """Test template output consistency across runs."""
    
    def test_deterministic_rendering(self):
        """Test that same input produces same output."""
        incident = Incident(
            id=7,
            kind="invariant",
            key="INV_test",
            severity="sev3",
            status="open",
            summary="Test incident",
            details={"test": "data"},
        )
        
        # Render multiple times
        outputs = [
            render_incident_issue(incident, template_type="invariant_failure")
            for _ in range(5)
        ]
        
        # All outputs should be identical
        assert len(set(outputs)) == 1, "Template rendering is non-deterministic"
    
    def test_no_extra_whitespace(self):
        """Test that templates don't have trailing whitespace."""
        incident = Incident(
            id=8,
            kind="budget",
            key="BUDGET_test",
            severity="sev2",
            status="open",
            summary="Test budget incident",
            details={"violation": {"agent": "test"}},
        )
        
        output = render_incident_issue(incident, template_type="budget_exceeded")
        
        # No trailing whitespace on lines
        for line in output.split("\n"):
            assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"
        
        # No trailing newlines (more than 1)
        assert not output.endswith("\n\n\n"), "Too many trailing newlines"


if __name__ == "__main__":
    # Run with UPDATE_GOLDEN=1 to update golden files
    pytest.main([__file__, "-v"])
