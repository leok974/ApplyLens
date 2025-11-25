"""
Tests for template rendering - Phase 5.4 PR2

Tests mustache-style template engine and incident issue rendering.
"""

import pytest
import tempfile
import os

from app.intervene.templates import TemplateRenderer, render_incident_issue
from app.models_incident import Incident


def test_template_renderer_simple_variable():
    """Test simple variable substitution."""
    renderer = TemplateRenderer()
    template = "Hello {{name}}!"
    context = {"name": "World"}

    result = renderer._render_string(template, context)

    assert result == "Hello World!"


def test_template_renderer_nested_variable():
    """Test nested variable access."""
    renderer = TemplateRenderer()
    template = "Agent: {{details.agent}}"
    context = {"details": {"agent": "gpt-4"}}

    result = renderer._render_string(template, context)

    assert result == "Agent: gpt-4"


def test_template_renderer_conditional_section():
    """Test conditional sections."""
    renderer = TemplateRenderer()
    template = "{{#show}}Visible{{/show}}"

    # Truthy
    result = renderer._render_string(template, {"show": True})
    assert result == "Visible"

    # Falsy
    result = renderer._render_string(template, {"show": False})
    assert result == ""


def test_template_renderer_inverted_section():
    """Test inverted sections."""
    renderer = TemplateRenderer()
    template = "{{^missing}}Not found{{/missing}}"

    # Key missing
    result = renderer._render_string(template, {})
    assert result == "Not found"

    # Key present
    result = renderer._render_string(template, {"missing": True})
    assert result == ""


def test_template_renderer_json_serialization():
    """Test JSON serialization for complex types."""
    renderer = TemplateRenderer()
    template = "Data: {{data}}"
    context = {"data": {"key": "value", "num": 123}}

    result = renderer._render_string(template, context)

    assert "key" in result
    assert "value" in result


def test_template_renderer_missing_variable():
    """Test handling of missing variables."""
    renderer = TemplateRenderer()
    template = "Hello {{missing}}!"
    context = {}

    result = renderer._render_string(template, context)

    # Should replace with empty string
    assert result == "Hello !"


def test_template_renderer_list_array():
    """Test array rendering."""
    renderer = TemplateRenderer()
    template = "Items: {{items}}"
    context = {"items": ["a", "b", "c"]}

    result = renderer._render_string(template, context)

    # Should be JSON array
    assert "a" in result
    assert "b" in result
    assert "c" in result


def test_template_renderer_load_template():
    """Test loading template from file."""
    # Create temp template file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# {{title}}\n\n{{body}}")
        temp_path = f.name

    try:
        # Create renderer with temp dir
        temp_dir = os.path.dirname(temp_path)
        temp_name = os.path.basename(temp_path)

        renderer = TemplateRenderer(template_dir=temp_dir)

        context = {"title": "Test", "body": "Content"}
        result = renderer.render(temp_name, context)

        assert "# Test" in result
        assert "Content" in result

    finally:
        os.unlink(temp_path)


def test_template_renderer_list_templates():
    """Test listing available templates."""
    renderer = TemplateRenderer()

    templates = renderer.list_templates()

    # Should find our templates
    assert "invariant_failure.md" in templates
    assert "budget_exceeded.md" in templates
    assert "planner_regression.md" in templates


def test_render_incident_issue_invariant():
    """Test rendering invariant failure issue."""
    incident = Incident(
        kind="invariant",
        key="task_123_inv_456",
        severity="sev2",
        status="open",
        summary="Invariant failed: data quality check",
        details={
            "agent": "gpt-4",
            "invariant_name": "completeness_check",
            "invariant_id": 456,
            "task_id": 123,
            "eval_result_id": 789,
            "failure_message": "Missing required fields",
            "evidence": {"missing_fields": ["email", "phone"]},
        },
    )

    title, body = render_incident_issue(incident)

    assert "Invariant Failure" in title
    assert "sev2" in title or "SEV2" in title
    assert "gpt-4" in body
    assert "completeness_check" in body
    assert "Missing required fields" in body


def test_render_incident_issue_budget():
    """Test rendering budget exceeded issue."""
    incident = Incident(
        kind="budget",
        key="budget_daily_2024-01-15",
        severity="sev2",
        status="open",
        summary="Budget exceeded for daily spend",
        details={
            "agent": "gpt-4",
            "budget_key": "daily",
            "spent": 1500.00,
            "limit": 1000.00,
            "overage": 500.00,
            "overage_pct": 50.0,
            "projected_daily_overage": 500.00,
        },
    )

    title, body = render_incident_issue(incident)

    assert "Budget Exceeded" in title
    assert "1500" in body or "1,500" in body
    assert "50" in body  # Overage percentage
    assert "daily" in body


def test_render_incident_issue_planner():
    """Test rendering planner regression issue."""
    incident = Incident(
        kind="planner",
        key="planner_v2.1.0_2024-01-15",
        severity="sev2",
        status="open",
        summary="Planner regression detected in v2.1.0",
        details={
            "version": "v2.1.0",
            "canary_percent": 10,
            "metrics": [
                {"name": "accuracy", "canary": 0.85, "baseline": 0.92, "delta": -0.07},
                {"name": "latency_p95", "canary": 2500, "baseline": 1800, "delta": 700},
            ],
            "affected_users": 1000,
            "rollback_available": True,
        },
    )

    title, body = render_incident_issue(incident)

    assert "Planner Regression" in title
    assert "v2.1.0" in title
    assert "accuracy" in body
    assert "rollback" in body.lower()


def test_render_incident_issue_unknown_kind():
    """Test rendering unknown incident kind (fallback)."""
    incident = Incident(
        kind="unknown",
        key="test_123",
        severity="sev3",
        status="open",
        summary="Unknown incident",
        details={},
    )

    # Should use invariant template as fallback
    title, body = render_incident_issue(incident)

    assert "Unknown" in title or "Incident" in title
    assert len(body) > 0


def test_template_variables_edge_cases():
    """Test edge cases in template variable handling."""
    renderer = TemplateRenderer()

    # Null value
    result = renderer._render_string("Value: {{val}}", {"val": None})
    assert result == "Value: null"

    # Zero
    result = renderer._render_string("Count: {{count}}", {"count": 0})
    assert result == "Count: 0"

    # Empty string
    result = renderer._render_string("Text: {{text}}", {"text": ""})
    assert result == "Text: "

    # Boolean
    result = renderer._render_string("Flag: {{flag}}", {"flag": True})
    assert result == "Flag: True"


def test_nested_value_parsing():
    """Test nested value parsing."""
    renderer = TemplateRenderer()

    context = {"level1": {"level2": {"level3": "deep_value"}}}

    value = renderer._get_nested_value(context, "level1.level2.level3")
    assert value == "deep_value"

    # Missing nested key
    value = renderer._get_nested_value(context, "level1.missing")
    assert value is None


def test_template_with_multiple_sections():
    """Test template with multiple conditional sections."""
    renderer = TemplateRenderer()

    template = """
{{#has_assignee}}Assigned to: {{assignee}}{{/has_assignee}}
{{^has_assignee}}Unassigned{{/has_assignee}}
Priority: {{priority}}
"""

    # With assignee
    result = renderer._render_string(
        template, {"has_assignee": True, "assignee": "alice", "priority": "high"}
    )
    assert "Assigned to: alice" in result
    assert "Unassigned" not in result

    # Without assignee
    result = renderer._render_string(
        template, {"has_assignee": False, "priority": "high"}
    )
    assert "Unassigned" in result
    assert "Assigned to:" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
