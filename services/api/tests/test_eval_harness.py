"""
Tests for eval harness.

Tests cover:
- Golden task loading
- Judge scoring
- Invariant checking
- Eval runner execution
- JSONL export
"""

import pytest
from app.eval.models import EvalTask, EvalSuite
from app.eval.judges import (
    RiskAccuracyJudge,
    SyncAccuracyJudge,
    InsightsQualityJudge,
    WarehouseHealthJudge,
    get_judge,
    get_invariant,
)
from app.eval.tasks import (
    get_inbox_tasks,
    get_inbox_suite,
    get_knowledge_tasks,
    get_insights_tasks,
    get_warehouse_tasks,
)
from app.eval.runner import EvalRunner, MockAgentExecutor


class TestGoldenTasks:
    """Test golden task collections."""

    def test_inbox_tasks_loaded(self):
        """Test inbox.triage tasks are loaded correctly."""
        tasks = get_inbox_tasks()

        assert len(tasks) > 0
        assert all(isinstance(t, EvalTask) for t in tasks)
        assert all(t.agent == "inbox.triage" for t in tasks)

        # Check phishing tasks exist
        phishing_tasks = [t for t in tasks if "phishing" in t.category]
        assert len(phishing_tasks) >= 2

        # Check for red_team tags
        red_team = [t for t in tasks if "red_team" in t.tags]
        assert len(red_team) > 0

    def test_knowledge_tasks_loaded(self):
        """Test knowledge.update tasks are loaded correctly."""
        tasks = get_knowledge_tasks()

        assert len(tasks) > 0
        assert all(t.agent == "knowledge.update" for t in tasks)

        # Check sync tasks
        sync_tasks = [t for t in tasks if t.category == "sync"]
        assert len(sync_tasks) >= 3

    def test_insights_tasks_loaded(self):
        """Test insights.write tasks are loaded correctly."""
        tasks = get_insights_tasks()

        assert len(tasks) > 0
        assert all(t.agent == "insights.write" for t in tasks)

        # Check analysis tasks
        analysis = [t for t in tasks if t.category == "analysis"]
        assert len(analysis) >= 3

    def test_warehouse_tasks_loaded(self):
        """Test warehouse.health tasks are loaded correctly."""
        tasks = get_warehouse_tasks()

        assert len(tasks) > 0
        assert all(t.agent == "warehouse.health" for t in tasks)

        # Check parity tasks
        parity = [t for t in tasks if t.category == "parity"]
        assert len(parity) >= 2

    def test_suite_structure(self):
        """Test eval suite structure."""
        suite = get_inbox_suite()

        assert suite.name == "inbox_triage_v1"
        assert suite.agent == "inbox.triage"
        assert len(suite.tasks) > 0
        assert len(suite.invariants) > 0

        # Test get_task
        first_task = suite.tasks[0]
        retrieved = suite.get_task(first_task.id)
        assert retrieved == first_task


class TestJudges:
    """Test judge scoring."""

    def test_risk_accuracy_judge_perfect(self):
        """Test RiskAccuracyJudge with perfect match."""
        judge = RiskAccuracyJudge()

        task = EvalTask(
            id="test",
            agent="inbox.triage",
            category="phishing_detection",
            objective="Test",
            expected_output={
                "risk_level": "high",
                "is_phishing": True,
                "category": "phishing",
            },
        )

        output = {
            "risk_level": "high",
            "is_phishing": True,
            "category": "phishing",
        }

        score, reasoning = judge.score(task, output)

        assert score == 100.0
        assert "exact match" in reasoning.lower()

    def test_risk_accuracy_judge_partial(self):
        """Test RiskAccuracyJudge with partial match."""
        judge = RiskAccuracyJudge()

        task = EvalTask(
            id="test",
            agent="inbox.triage",
            category="risk_scoring",
            objective="Test",
            expected_output={
                "risk_level": "high",
                "is_phishing": True,
            },
        )

        output = {
            "risk_level": "medium",  # Off by 1
            "is_phishing": True,
        }

        score, reasoning = judge.score(task, output)

        assert 50 < score < 100
        assert "close" in reasoning.lower()

    def test_sync_accuracy_judge(self):
        """Test SyncAccuracyJudge."""
        judge = SyncAccuracyJudge()

        task = EvalTask(
            id="test",
            agent="knowledge.update",
            category="sync",
            objective="Test",
            expected_output={
                "items_synced": 100,
                "synonyms_preserved": True,
                "conflicts_resolved": 5,
            },
        )

        output = {
            "items_synced": 100,
            "synonyms_preserved": True,
            "conflicts_resolved": 5,
        }

        score, reasoning = judge.score(task, output)

        assert score == 100.0

    def test_insights_quality_judge(self):
        """Test InsightsQualityJudge."""
        judge = InsightsQualityJudge()

        task = EvalTask(
            id="test",
            agent="insights.write",
            category="analysis",
            objective="Test",
            expected_output={
                "metrics_count": 5,
                "trends": ["trend1", "trend2"],
            },
        )

        output = {
            "metrics_count": 5,
            "trends": ["trend1", "trend2"],
            "has_summary": True,
            "has_recommendations": True,
        }

        score, reasoning = judge.score(task, output)

        assert score == 100.0

    def test_warehouse_health_judge(self):
        """Test WarehouseHealthJudge."""
        judge = WarehouseHealthJudge()

        task = EvalTask(
            id="test",
            agent="warehouse.health",
            category="health_check",
            objective="Test",
            expected_output={
                "is_healthy": True,
                "issues_count": 0,
                "parity_ok": True,
            },
        )

        output = {
            "is_healthy": True,
            "issues_count": 0,
            "parity_ok": True,
        }

        score, reasoning = judge.score(task, output)

        assert score == 100.0

    def test_judge_registry(self):
        """Test judge registry."""
        judge = get_judge("inbox.triage")
        assert isinstance(judge, RiskAccuracyJudge)

        judge = get_judge("knowledge.update")
        assert isinstance(judge, SyncAccuracyJudge)

        with pytest.raises(ValueError):
            get_judge("unknown.agent")


class TestInvariants:
    """Test invariant checking."""

    def test_phishing_invariant_pass(self):
        """Test phishing invariant passes when phishing is detected."""
        inv = get_invariant("no_false_negatives_phishing")

        task = EvalTask(
            id="test",
            agent="inbox.triage",
            category="phishing_detection",
            objective="Test",
            expected_output={"is_phishing": True},
        )

        output = {"is_phishing": True, "risk_level": "high"}

        passed, reason = inv.check(task, output)

        assert passed
        assert "detected" in reason.lower()

    def test_phishing_invariant_fail(self):
        """Test phishing invariant fails on false negative."""
        inv = get_invariant("no_false_negatives_phishing")

        task = EvalTask(
            id="test",
            agent="inbox.triage",
            category="phishing_detection",
            objective="Test",
            expected_output={"is_phishing": True},
        )

        output = {"is_phishing": False, "risk_level": "low"}

        passed, reason = inv.check(task, output)

        assert not passed
        assert "false negative" in reason.lower()

    def test_sync_completion_invariant(self):
        """Test sync completion invariant."""
        inv = get_invariant("sync_completion")

        task = EvalTask(
            id="test",
            agent="knowledge.update",
            category="sync",
            objective="Test",
            expected_output={"items_synced": 100},
        )

        # Pass case
        output = {"items_synced": 98}
        passed, reason = inv.check(task, output)
        assert passed

        # Fail case
        output = {"items_synced": 80}
        passed, reason = inv.check(task, output)
        assert not passed

    def test_insights_data_quality_invariant(self):
        """Test insights data quality invariant."""
        inv = get_invariant("insights_data_quality")

        task = EvalTask(
            id="test",
            agent="insights.write",
            category="analysis",
            objective="Test",
        )

        # Pass case
        output = {"metrics_count": 5}
        passed, reason = inv.check(task, output)
        assert passed

        # Fail case
        output = {"metrics_count": 2}
        passed, reason = inv.check(task, output)
        assert not passed

    def test_warehouse_parity_invariant(self):
        """Test warehouse parity invariant."""
        inv = get_invariant("warehouse_parity_detection")

        task = EvalTask(
            id="test",
            agent="warehouse.health",
            category="parity",
            objective="Test",
            expected_output={"parity_ok": False},  # Expect issue
        )

        # Pass case: detected the issue
        output = {"parity_ok": False, "is_healthy": False}
        passed, reason = inv.check(task, output)
        assert passed

        # Fail case: missed the issue
        output = {"parity_ok": True, "is_healthy": True}
        passed, reason = inv.check(task, output)
        assert not passed


class TestMockExecutor:
    """Test mock agent executor."""

    def test_inbox_mock_phishing(self):
        """Test inbox mock detects phishing."""
        executor = MockAgentExecutor()

        output = executor.execute(
            "inbox.triage",
            "Analyze email",
            {
                "subject": "Urgent: Verify your account",
                "sender": "noreply@suspicious-domain.net",
                "body": "Click here to verify...",
                "domain_age_days": 5,
            },
        )

        assert output["risk_level"] == "high"
        assert output["is_phishing"] is True

    def test_inbox_mock_trusted(self):
        """Test inbox mock recognizes trusted sender."""
        executor = MockAgentExecutor()

        output = executor.execute(
            "inbox.triage",
            "Analyze email",
            {
                "subject": "Meeting notes",
                "sender": "colleague@company.com",
                "sender_in_contacts": True,
            },
        )

        assert output["risk_level"] == "low"
        assert output["is_phishing"] is False

    def test_knowledge_mock_sync(self):
        """Test knowledge mock syncs items."""
        executor = MockAgentExecutor()

        output = executor.execute(
            "knowledge.update",
            "Sync 100 items",
            {"entry_count": 100, "has_conflicts": False},
        )

        assert output["items_synced"] >= 95
        assert output["synonyms_preserved"] is True

    def test_insights_mock_report(self):
        """Test insights mock generates report."""
        executor = MockAgentExecutor()

        output = executor.execute(
            "insights.write",
            "Generate report",
            {
                "time_range": "7d",
                "report_type": "productivity",
                "metrics": ["email_count", "response_time"],
            },
        )

        assert output["metrics_count"] >= 2
        assert output["has_summary"] is True

    def test_warehouse_mock_health(self):
        """Test warehouse mock checks health."""
        executor = MockAgentExecutor()

        output = executor.execute(
            "warehouse.health",
            "Check health",
            {
                "source_count": 1000,
                "target_count": 1000,
                "check_types": ["parity", "freshness"],
            },
        )

        assert output["is_healthy"] is True
        assert output["parity_ok"] is True


class TestEvalRunner:
    """Test eval runner."""

    def test_run_small_suite(self, tmp_path):
        """Test running a small eval suite."""
        runner = EvalRunner(use_mock_executor=True, output_dir=tmp_path)

        # Create small test suite
        suite = EvalSuite(
            name="test_suite",
            agent="inbox.triage",
            tasks=[
                EvalTask(
                    id="test.001",
                    agent="inbox.triage",
                    category="test",
                    objective="Test task",
                    context={"subject": "Test", "sender": "test@example.com"},
                    expected_output={"risk_level": "low"},
                ),
            ],
        )

        run = runner.run_suite(suite)

        assert run.suite_name == "test_suite"
        assert run.agent == "inbox.triage"
        assert run.total_tasks == 1
        assert run.success_rate == 1.0
        assert run.avg_quality_score > 0

    def test_run_inbox_suite(self, tmp_path):
        """Test running full inbox suite."""
        runner = EvalRunner(use_mock_executor=True, output_dir=tmp_path)

        suite = get_inbox_suite()
        run = runner.run_suite(suite)

        assert run.total_tasks == len(suite.tasks)
        assert run.success_rate > 0.8
        assert run.avg_quality_score > 60

        # Check JSONL export
        jsonl_files = list(tmp_path.glob("*.jsonl"))
        assert len(jsonl_files) == 1

        # Verify JSONL content
        with open(jsonl_files[0]) as f:
            lines = f.readlines()
            assert len(lines) == len(suite.tasks) + 1  # Summary + results

    def test_invariant_tracking(self, tmp_path):
        """Test invariant pass/fail tracking."""
        runner = EvalRunner(use_mock_executor=True, output_dir=tmp_path)

        # Create suite with invariants
        suite = EvalSuite(
            name="test_invariants",
            agent="inbox.triage",
            tasks=[
                EvalTask(
                    id="phishing.001",
                    agent="inbox.triage",
                    category="phishing_detection",
                    objective="Detect phishing",
                    context={
                        "subject": "Urgent: Verify account",
                        "sender": "phishing@suspicious.net",
                        "domain_age_days": 2,
                    },
                    expected_output={"is_phishing": True},
                    invariants=["no_false_negatives_phishing"],
                ),
            ],
        )

        run = runner.run_suite(suite)

        assert run.invariants_passed > 0
        assert run.invariants_failed == 0

    def test_difficulty_breakdown(self, tmp_path):
        """Test quality score breakdown by difficulty."""
        runner = EvalRunner(use_mock_executor=True, output_dir=tmp_path)

        suite = EvalSuite(
            name="test_difficulty",
            agent="inbox.triage",
            tasks=[
                EvalTask(
                    id="easy.001",
                    agent="inbox.triage",
                    category="test",
                    objective="Easy task",
                    context={"sender_in_contacts": True},
                    difficulty="easy",
                ),
                EvalTask(
                    id="hard.001",
                    agent="inbox.triage",
                    category="test",
                    objective="Hard task",
                    context={"subject": "", "body": ""},
                    difficulty="hard",
                ),
            ],
        )

        run = runner.run_suite(suite)

        assert "easy" in run.quality_by_difficulty
        assert "hard" in run.quality_by_difficulty
        # Both should have scores (actual ordering depends on mock logic)
        assert run.quality_by_difficulty["easy"] > 0
        assert run.quality_by_difficulty["hard"] > 0
