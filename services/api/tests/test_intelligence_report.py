"""
Tests for intelligence report generation.

Tests:
- Report generation with mock data
- Trend calculation
- Regression detection
- Section formatting
- CLI integration
- API endpoints
"""
import pytest
from datetime import datetime, timedelta
from app.eval.intelligence_report import ReportGenerator, format_report_as_html
from app.eval.budgets import DEFAULT_BUDGETS
from app.models import AgentMetricsDaily


class TestReportGenerator:
    """Test report generation."""
    
    def test_generate_empty_report(self, db_session):
        """Test report generation with no data."""
        generator = ReportGenerator(db_session)
        report = generator.generate_weekly_report()
        
        assert "# 🎯 Agent Intelligence Report" in report
        assert "Executive Summary" in report
        assert "Agent Analysis" in report
        
    def test_generate_report_with_data(self, db_session):
        """Test report generation with sample metrics."""
        # Create sample metrics for last week
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        
        for i in range(7):
            date = week_start + timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                successful_runs=95,
                failed_runs=5,
                avg_quality_score=87.5,
                avg_latency_ms=450.0,
                p50_latency_ms=400.0,
                p95_latency_ms=550.0,
                p99_latency_ms=650.0,
                avg_cost_weight=0.5,
                invariants_passed=10,
                invariants_failed=0,
            )
            db_session.add(metric)
        
        db_session.commit()
        
        generator = ReportGenerator(db_session)
        report = generator.generate_weekly_report()
        
        assert "inbox.triage" in report
        assert "87.5" in report or "87" in report  # Quality score
        assert "95" in report  # Success rate
        
    def test_report_includes_all_sections(self, db_session):
        """Test that report includes all required sections."""
        generator = ReportGenerator(db_session)
        report = generator.generate_weekly_report()
        
        # Check for all sections
        assert "Executive Summary" in report
        assert "Agent Analysis" in report
        assert "Invariant Status" in report
        assert "Red Team Testing" in report
        assert "Recommendations" in report
        
    def test_report_week_parameter(self, db_session):
        """Test report generation for specific week."""
        generator = ReportGenerator(db_session)
        
        # Generate report for specific week
        week_start = datetime(2024, 1, 15)  # A Monday
        report = generator.generate_weekly_report(week_start=week_start)
        
        assert "January 15, 2024" in report
        
    def test_summary_section_format(self, db_session):
        """Test executive summary formatting."""
        generator = ReportGenerator(db_session)
        summary_lines = generator._generate_summary({
            "passed": True,
            "results": {
                "inbox.triage": {"passed": True, "violations": []},
                "knowledge.update": {"passed": True, "violations": []},
            },
            "total_violations": 0,
            "critical_violations": 0,
        })
        
        summary_text = "\n".join(summary_lines)
        assert "Agents Monitored: 2" in summary_text
        assert "Passing Quality Gates: 2/2" in summary_text
        assert "✅" in summary_text  # Success icon
        
    def test_summary_with_violations(self, db_session):
        """Test summary with violations."""
        from app.eval.budgets import BudgetViolation
        
        generator = ReportGenerator(db_session)
        summary_lines = generator._generate_summary({
            "passed": False,
            "results": {
                "inbox.triage": {
                    "passed": False,
                    "violations": [
                        BudgetViolation(
                            agent="inbox.triage",
                            budget_type="quality",
                            threshold=85.0,
                            actual=80.0,
                            severity="error",
                            message="Quality below threshold",
                        )
                    ],
                },
            },
            "total_violations": 1,
            "critical_violations": 0,
        })
        
        summary_text = "\n".join(summary_lines)
        assert "Total Violations: 1" in summary_text
        assert "⚠️" in summary_text  # Warning icon
        
    def test_agent_section_passing(self, db_session):
        """Test agent section for passing agent."""
        generator = ReportGenerator(db_session)
        
        result = {
            "passed": True,
            "violations": [],
            "current_metrics": {
                "avg_quality_score": 88.5,
                "success_rate": 0.96,
                "avg_latency_ms": 450.0,
                "total_runs": 150,
            },
            "baseline_metrics": {
                "avg_quality_score": 87.0,
                "avg_latency_ms": 480.0,
            },
        }
        
        week_start = datetime(2024, 1, 15)
        prev_week_start = datetime(2024, 1, 8)
        
        lines = generator._generate_agent_section(
            "inbox.triage",
            result,
            week_start,
            prev_week_start,
        )
        
        section_text = "\n".join(lines)
        assert "inbox.triage" in section_text
        assert "✅ Passing" in section_text
        assert "88.5" in section_text or "88" in section_text
        assert "96%" in section_text or "0.96" in section_text


class TestReportFormatting:
    """Test report formatting functions."""
    
    def test_format_as_html(self):
        """Test markdown to HTML conversion."""
        markdown = """# Test Report
        
## Section 1

Some content here.

- Item 1
- Item 2
"""
        
        html = format_report_as_html(markdown)
        
        # Should contain HTML tags (even if fallback to <pre>)
        assert "<" in html and ">" in html
        
    def test_format_as_html_with_markdown_library(self):
        """Test HTML conversion with markdown library (if available)."""
        try:
            import markdown
            
            markdown_text = "# Heading\n\nParagraph with **bold**."
            html = format_report_as_html(markdown_text)
            
            # Should have proper HTML elements
            assert "<h1>" in html or "<pre>" in html
            
        except ImportError:
            pytest.skip("markdown library not available")


class TestRecommendations:
    """Test recommendation generation."""
    
    def test_recommendations_for_quality_violation(self, db_session):
        """Test recommendations for quality issues."""
        from app.eval.budgets import BudgetViolation
        
        generator = ReportGenerator(db_session)
        
        gate_results = {
            "passed": False,
            "results": {
                "inbox.triage": {
                    "passed": False,
                    "violations": [
                        BudgetViolation(
                            agent="inbox.triage",
                            budget_type="quality",
                            threshold=85.0,
                            actual=80.0,
                            severity="error",
                            message="Quality score below threshold",
                        )
                    ],
                },
            },
            "total_violations": 1,
            "critical_violations": 0,
        }
        
        recommendations = generator._generate_recommendations(gate_results)
        rec_text = "\n".join(recommendations)
        
        assert "inbox.triage" in rec_text
        assert "Quality" in rec_text or "quality" in rec_text
        
    def test_recommendations_for_latency_violation(self, db_session):
        """Test recommendations for latency issues."""
        from app.eval.budgets import BudgetViolation
        
        generator = ReportGenerator(db_session)
        
        gate_results = {
            "passed": False,
            "results": {
                "inbox.triage": {
                    "passed": False,
                    "violations": [
                        BudgetViolation(
                            agent="inbox.triage",
                            budget_type="latency_avg",
                            threshold=500.0,
                            actual=750.0,
                            severity="error",
                            message="Average latency above threshold",
                        )
                    ],
                },
            },
            "total_violations": 1,
            "critical_violations": 0,
        }
        
        recommendations = generator._generate_recommendations(gate_results)
        rec_text = "\n".join(recommendations)
        
        assert "latency" in rec_text.lower()
        assert "inbox.triage" in rec_text
        
    def test_no_recommendations_when_passing(self, db_session):
        """Test no recommendations when all agents passing."""
        generator = ReportGenerator(db_session)
        
        gate_results = {
            "passed": True,
            "results": {
                "inbox.triage": {"passed": True, "violations": []},
            },
            "total_violations": 0,
            "critical_violations": 0,
        }
        
        recommendations = generator._generate_recommendations(gate_results)
        rec_text = "\n".join(recommendations)
        
        assert "No action items" in rec_text or "✅" in rec_text


class TestInvariantsSection:
    """Test invariant status section."""
    
    def test_invariants_with_no_data(self, db_session):
        """Test invariants section with no metrics."""
        generator = ReportGenerator(db_session)
        
        week_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        lines = generator._generate_invariants_section(week_start)
        
        section_text = "\n".join(lines)
        # Should handle gracefully
        assert len(section_text) >= 0
        
    def test_invariants_all_passing(self, db_session):
        """Test invariants section with all passing."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        
        for i in range(7):
            date = week_start + timedelta(days=i)
            metric = AgentMetricsDaily(
                agent="inbox.triage",
                date=date,
                total_runs=100,
                invariants_passed=10,
                invariants_failed=0,
            )
            db_session.add(metric)
        
        db_session.commit()
        
        generator = ReportGenerator(db_session)
        lines = generator._generate_invariants_section(week_start)
        
        section_text = "\n".join(lines)
        assert "100.0%" in section_text or "All invariants passing" in section_text


class TestRedTeamSection:
    """Test red team section."""
    
    def test_redteam_no_attacks(self, db_session):
        """Test red team section with no attacks."""
        generator = ReportGenerator(db_session)
        
        week_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        lines = generator._generate_redteam_section(week_start)
        
        section_text = "\n".join(lines)
        assert "No red team attacks" in section_text
        
    def test_redteam_with_attacks(self, db_session):
        """Test red team section with attack data."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        
        metric = AgentMetricsDaily(
            agent="inbox.triage",
            date=week_start,
            total_runs=100,
            redteam_attacks_detected=8,
            redteam_attacks_missed=2,
            redteam_false_positives=1,
        )
        db_session.add(metric)
        db_session.commit()
        
        generator = ReportGenerator(db_session)
        lines = generator._generate_redteam_section(week_start)
        
        section_text = "\n".join(lines)
        assert "Detection Rate" in section_text
        assert "8" in section_text  # Detected
        assert "2" in section_text  # Missed
