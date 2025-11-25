"""Tests for planner decision logging and weekly rollup.

Tests:
- Planner metadata persistence in audit logs
- Weekly diff analysis
- Report generation
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from app.cron.planner_rollup import analyze_planner_diffs, generate_weekly_report
from app.models import AgentAuditLog


class TestPlannerAuditLogging:
    """Test planner metadata persistence."""

    def test_planner_meta_in_audit_log(self):
        """Planner metadata should be persisted in audit log plan field."""
        from app.agents.audit import AgentAuditor

        mock_db = Mock()
        auditor = AgentAuditor(db_session=mock_db)

        # Mock successful commit
        mock_db.add = Mock()
        mock_db.commit = Mock()

        planner_meta = {
            "selected": "v2",
            "shadow": {"agent": "inbox_triage"},
            "diff": {"agent_changed": False},
            "latency_ms": 45.2,
        }

        auditor.log_start(
            run_id="test-123",
            agent="inbox_triage",
            objective="Process email",
            plan={"agent": "inbox_triage", "steps": ["a", "b"]},
            planner_meta=planner_meta,
        )

        # Verify plan includes planner_meta
        call_args = mock_db.add.call_args[0][0]
        assert "planner_meta" in call_args.plan
        assert call_args.plan["planner_meta"]["selected"] == "v2"


class TestPlannerRollup:
    """Test weekly planner diff analysis."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    def test_analyze_planner_diffs_counts_v1_v2(self, mock_db):
        """Should correctly count V1 and V2 runs."""
        # Mock runs
        runs = []

        # 7 V1 runs
        for i in range(7):
            run = Mock(spec=AgentAuditLog)
            run.run_id = f"v1-{i}"
            run.objective = "Test objective"
            run.started_at = datetime.utcnow()
            run.plan = {
                "planner_meta": {"selected": "v1", "diff": {"agent_changed": False}}
            }
            runs.append(run)

        # 3 V2 runs
        for i in range(3):
            run = Mock(spec=AgentAuditLog)
            run.run_id = f"v2-{i}"
            run.objective = "Test objective"
            run.started_at = datetime.utcnow()
            run.plan = {
                "planner_meta": {"selected": "v2", "diff": {"agent_changed": False}}
            }
            runs.append(run)

        mock_db.query.return_value.filter.return_value.all.return_value = runs

        start = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow()

        analysis = analyze_planner_diffs(mock_db, start, end)

        assert analysis["v1_count"] == 7
        assert analysis["v2_count"] == 3
        assert analysis["total_runs"] == 10
        assert analysis["v2_pct"] == 30.0

    def test_analyze_planner_diffs_tracks_agent_changes(self, mock_db):
        """Should track agent selection differences."""
        runs = []

        # 5 runs where V1 != V2
        for i in range(5):
            run = Mock(spec=AgentAuditLog)
            run.run_id = f"run-{i}"
            run.objective = "Email triage"
            run.started_at = datetime.utcnow()
            run.plan = {
                "planner_meta": {
                    "selected": "v2",
                    "diff": {
                        "agent_changed": True,
                        "v1_agent": "inbox_triage",
                        "v2_agent": "inbox_priority",
                    },
                }
            }
            runs.append(run)

        # 15 runs where V1 == V2
        for i in range(15):
            run = Mock(spec=AgentAuditLog)
            run.run_id = f"run-match-{i}"
            run.objective = "Test"
            run.started_at = datetime.utcnow()
            run.plan = {
                "planner_meta": {"selected": "v1", "diff": {"agent_changed": False}}
            }
            runs.append(run)

        mock_db.query.return_value.filter.return_value.all.return_value = runs

        start = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow()

        analysis = analyze_planner_diffs(mock_db, start, end)

        assert analysis["agent_change_rate"] == 25.0  # 5/20 = 25%
        assert len(analysis["top_disagreements"]) > 0

    def test_analyze_planner_diffs_handles_no_runs(self, mock_db):
        """Should handle case with no runs."""
        mock_db.query.return_value.filter.return_value.all.return_value = []

        start = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow()

        analysis = analyze_planner_diffs(mock_db, start, end)

        assert analysis["total_runs"] == 0
        assert analysis["v2_pct"] == 0.0


class TestReportGeneration:
    """Test weekly report markdown generation."""

    def test_generate_weekly_report_format(self):
        """Should generate valid markdown report."""
        analysis = {
            "start_date": datetime(2025, 10, 10),
            "end_date": datetime(2025, 10, 17),
            "total_runs": 100,
            "v1_count": 85,
            "v2_count": 15,
            "v2_pct": 15.0,
            "agent_change_rate": 12.0,
            "top_disagreements": [
                (("inbox_triage", "inbox_priority"), 8),
                (("knowledge_update", "knowledge_validate"), 4),
            ],
            "notable_diffs": [],
        }

        report = generate_weekly_report(analysis)

        assert "# Planner Weekly Report" in report
        assert "2025-W41" in report
        assert "Total Runs:** 100" in report
        assert "V2 (canary):** 15 runs (15.0%)" in report
        assert "Agent change rate:** 12.0%" in report

    def test_generate_weekly_report_recommendations(self):
        """Should include actionable recommendations."""
        analysis = {
            "start_date": datetime(2025, 10, 10),
            "end_date": datetime(2025, 10, 17),
            "total_runs": 100,
            "v1_count": 98,
            "v2_count": 2,
            "v2_pct": 2.0,
            "agent_change_rate": 45.0,
            "top_disagreements": [],
            "notable_diffs": [],
        }

        report = generate_weekly_report(analysis)

        assert "Recommendations" in report
        assert "Increase canary" in report or "canary" in report.lower()
        assert "High disagreement" in report or "disagreement" in report.lower()

    def test_generate_weekly_report_with_divergences(self):
        """Should include table of notable divergences."""
        analysis = {
            "start_date": datetime(2025, 10, 10),
            "end_date": datetime(2025, 10, 17),
            "total_runs": 50,
            "v1_count": 40,
            "v2_count": 10,
            "v2_pct": 20.0,
            "agent_change_rate": 10.0,
            "top_disagreements": [],
            "notable_diffs": [
                {
                    "run_id": "abc-123",
                    "objective": "Process email about job application",
                    "v1_agent": "inbox_triage",
                    "v2_agent": "inbox_priority",
                    "selected": "v2",
                    "started_at": datetime.utcnow(),
                }
            ],
        }

        report = generate_weekly_report(analysis)

        assert "Notable Divergences" in report
        assert "inbox_triage" in report
        assert "inbox_priority" in report
