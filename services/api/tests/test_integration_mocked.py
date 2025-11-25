"""
Integration Tests with Mocks - Phase 5.4 PR6

End-to-end tests using mock services.
Tests full flow without external dependencies.
"""

import pytest
from unittest.mock import patch

from app.models_incident import Incident
from app.intervene.adapters.github import GitHubAdapter
from app.intervene.adapters.gitlab import GitLabAdapter
from app.intervene.adapters.jira import JiraAdapter
from app.intervene.actions.dbt import RerunDbtAction, RefreshDbtDependenciesAction
from app.intervene.actions.elastic import ClearCacheAction, RefreshSynonymsAction
from app.intervene.actions.planner import RollbackPlannerAction, AdjustCanarySplitAction

from tests.mocks.issue_trackers import (
    mock_github,
    mock_gitlab,
    mock_jira,
    reset_all_mocks as reset_trackers,
)
from tests.mocks.action_executors import (
    mock_dbt,
    mock_elasticsearch,
    mock_planner,
    reset_all_mocks as reset_executors,
)


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks before each test."""
    reset_trackers()
    reset_executors()
    yield
    reset_trackers()
    reset_executors()


class TestIssueCreationFlow:
    """Test end-to-end issue creation flow with mocks."""

    def test_github_issue_creation_from_incident(self):
        """Test GitHub issue created from incident."""
        incident = Incident(
            id=1,
            kind="invariant",
            key="INV_test",
            severity="sev1",
            status="open",
            summary="Test invariant failure",
            details={"invariant": {"id": "test_inv"}},
        )

        config = {
            "token": "fake-token",
            "owner": "test-owner",
            "repo": "test-repo",
        }

        # Mock requests
        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_github.create_issue(
                owner=config["owner"],
                repo=config["repo"],
                title=incident.summary,
                body="Mock body",
                labels=["sev1", "invariant"],
            )

            adapter = GitHubAdapter(config)
            issue_url = adapter.create_issue(
                title=incident.summary,
                body="Mock body",
                labels=["sev1", "invariant"],
            )

            assert issue_url is not None
            assert "github.com" in issue_url
            assert len(mock_github.issues_created) == 1
            assert mock_github.issues_created[0]["title"] == incident.summary

    def test_gitlab_issue_creation_from_incident(self):
        """Test GitLab issue created from incident."""
        incident = Incident(
            id=2,
            kind="budget",
            key="BUDGET_test_latency",
            severity="sev2",
            status="open",
            summary="Test budget violation",
            details={"violation": {"budget_type": "latency"}},
        )

        config = {
            "token": "fake-token",
            "project_id": "test-project",
        }

        # Mock requests
        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_gitlab.create_issue(
                project_id=config["project_id"],
                title=incident.summary,
                description="Mock description",
                labels=["sev2", "budget"],
            )

            adapter = GitLabAdapter(config)
            issue_url = adapter.create_issue(
                title=incident.summary,
                body="Mock description",
                labels=["sev2", "budget"],
            )

            assert issue_url is not None
            assert "gitlab.com" in issue_url
            assert len(mock_gitlab.issues_created) == 1

    def test_jira_issue_creation_from_incident(self):
        """Test Jira issue created from incident."""
        incident = Incident(
            id=3,
            kind="planner",
            key="PLANNER_REG_v1.0.0",
            severity="sev1",
            status="open",
            summary="Test planner regression",
            details={"version": "v1.0.0"},
        )

        config = {
            "token": "fake-token",
            "server": "https://jira.example.com",
            "project_key": "TEST",
        }

        # Mock requests
        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_jira.create_issue(
                project_key=config["project_key"],
                summary=incident.summary,
                description={"version": 1, "type": "doc", "content": []},
                issue_type="Bug",
                labels=["sev1", "planner"],
            )

            adapter = JiraAdapter(config)
            issue_key = adapter.create_issue(
                title=incident.summary,
                body="Mock ADF description",
                labels=["sev1", "planner"],
            )

            assert issue_key is not None
            assert issue_key.startswith("TEST-")
            assert len(mock_jira.issues_created) == 1


class TestActionExecutionFlow:
    """Test end-to-end action execution flow with mocks."""

    def test_dbt_rerun_action_execution(self):
        """Test DBT rerun action with mock executor."""
        action = RerunDbtAction(
            task_id="task-123",
            models=["model_a", "model_b"],
            full_refresh=False,
            upstream=False,
            threads=4,
        )

        # Patch DBT executor
        with patch("app.intervene.actions.dbt._execute_dbt_command") as mock_exec:
            mock_exec.return_value = mock_dbt.run_models(
                models=action.models,
                full_refresh=action.full_refresh,
                upstream=action.upstream,
                threads=action.threads,
            )

            result = action.execute()

            assert result.status == "success"
            assert "Successfully ran 2 model(s)" in result.message
            assert len(mock_dbt.commands_executed) == 1
            assert mock_dbt.commands_executed[0]["type"] == "run"

    def test_dbt_refresh_dependencies_action(self):
        """Test DBT refresh dependencies action."""
        action = RefreshDbtDependenciesAction(task_id="task-456")

        with patch("app.intervene.actions.dbt._execute_dbt_command") as mock_exec:
            mock_exec.return_value = mock_dbt.refresh_dependencies()

            result = action.execute()

            assert result.status == "success"
            assert "Dependencies refreshed" in result.message
            assert len(mock_dbt.commands_executed) == 1
            assert mock_dbt.commands_executed[0]["type"] == "deps"

    def test_elasticsearch_clear_cache_action(self):
        """Test Elasticsearch clear cache action."""
        action = ClearCacheAction(
            index_name="test-index",
            cache_types=["query", "request"],
        )

        with patch("app.intervene.actions.elastic._get_es_client") as mock_client:
            mock_client.return_value = mock_elasticsearch

            result = action.execute()

            assert result.status == "success"
            assert len(mock_elasticsearch.caches_cleared) == 1
            assert "test-index" in mock_elasticsearch.caches_cleared

    def test_elasticsearch_refresh_synonyms_action(self):
        """Test Elasticsearch refresh synonyms action."""
        action = RefreshSynonymsAction(
            index_name="test-index",
            synonym_filter="synonyms_filter",
            reindex=False,
        )

        with patch("app.intervene.actions.elastic._get_es_client") as mock_client:
            mock_client.return_value = mock_elasticsearch

            result = action.execute()

            assert result.status == "success"
            assert "test-index" in mock_elasticsearch.indices_closed
            assert "test-index" in mock_elasticsearch.indices_opened

    def test_planner_rollback_action(self):
        """Test planner rollback action."""
        action = RollbackPlannerAction(
            from_version="v1.1.0-canary",
            to_version="v1.0.0",
            immediate=True,
        )

        with patch("app.intervene.actions.planner._get_planner_client") as mock_client:
            mock_client.return_value = mock_planner

            result = action.execute()

            assert result.status == "success"
            assert "Rolled back to v1.0.0" in result.message
            assert len(mock_planner.rollbacks) == 1
            assert mock_planner.rollbacks[0]["to_version"] == "v1.0.0"

    def test_planner_adjust_canary_action(self):
        """Test planner adjust canary split action."""
        action = AdjustCanarySplitAction(
            version="v1.1.0-canary",
            target_percent=25,
            gradual=True,
        )

        with patch("app.intervene.actions.planner._get_planner_client") as mock_client:
            mock_client.return_value = mock_planner

            result = action.execute()

            assert result.status == "success"
            assert "25% traffic" in result.message
            assert len(mock_planner.traffic_adjustments) == 1
            assert mock_planner.traffic_adjustments[0]["to_pct"] == 25


class TestFailureHandling:
    """Test error handling with mocks."""

    def test_dbt_failure_handling(self):
        """Test DBT action handles failures gracefully."""
        action = RerunDbtAction(
            task_id="task-fail",
            models=["failing_model"],
            full_refresh=False,
            upstream=False,
            threads=4,
        )

        # Configure mock to fail
        mock_dbt.should_fail = True
        mock_dbt.failure_message = "dbt compilation error"

        with patch("app.intervene.actions.dbt._execute_dbt_command") as mock_exec:
            mock_exec.return_value = mock_dbt.run_models(
                models=action.models,
                full_refresh=False,
                upstream=False,
                threads=4,
            )

            result = action.execute()

            assert result.status == "failed"
            assert "compilation error" in result.message

    def test_elasticsearch_failure_handling(self):
        """Test Elasticsearch action handles failures gracefully."""
        action = ClearCacheAction(
            index_name="failing-index",
            cache_types=["query"],
        )

        # Configure mock to fail
        mock_elasticsearch.should_fail = True
        mock_elasticsearch.failure_message = "Index not found"

        with patch("app.intervene.actions.elastic._get_es_client") as mock_client:
            mock_client.return_value = mock_elasticsearch

            result = action.execute()

            assert result.status == "failed"
            assert "not found" in result.message.lower()

    def test_planner_failure_handling(self):
        """Test planner action handles failures gracefully."""
        action = RollbackPlannerAction(
            from_version="v1.1.0-canary",
            to_version="v1.0.0",
            immediate=False,
        )

        # Configure mock to fail
        mock_planner.should_fail = True
        mock_planner.failure_message = "Deployment timeout"

        with patch("app.intervene.actions.planner._get_planner_client") as mock_client:
            mock_client.return_value = mock_planner

            result = action.execute()

            assert result.status == "failed"
            assert "timeout" in result.message.lower()


class TestDryRunFlow:
    """Test dry-run mode with mocks."""

    def test_dbt_dry_run_no_execution(self):
        """Test DBT dry-run doesn't execute commands."""
        action = RerunDbtAction(
            task_id="task-dry",
            models=["model_x"],
            full_refresh=True,
            upstream=False,
            threads=4,
        )

        result = action.dry_run()

        assert result.status == "dry_run_success"
        assert "dbt run" in result.message
        assert len(mock_dbt.commands_executed) == 0  # No actual execution
        assert result.estimated_duration is not None
        assert result.estimated_cost is not None

    def test_planner_dry_run_no_deployment(self):
        """Test planner dry-run doesn't deploy."""
        action = RollbackPlannerAction(
            from_version="v1.1.0-canary",
            to_version="v1.0.0",
            immediate=True,
        )

        result = action.dry_run()

        assert result.status == "dry_run_success"
        assert "rollback" in result.message.lower()
        assert len(mock_planner.rollbacks) == 0  # No actual rollback
        assert result.estimated_duration is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
