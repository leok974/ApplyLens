"""
Integration tests for watcher + adapters - Phase 5.4 PR2

Tests that incidents auto-create external issues when configured.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.intervene.watcher import InvariantWatcher
from app.models_incident import Incident
from app.models_runtime import RuntimeSettings


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    return db


@pytest.fixture
def github_config():
    """Sample GitHub configuration."""
    return {
        "provider": "github",
        "config": {
            "token": "ghp_test123",
            "owner": "testorg",
            "repo": "testrepo",
        },
    }


def test_watcher_creates_external_issue_when_configured(mock_db, github_config):
    """Test that watcher creates external issue when provider is configured."""

    # Setup: Create runtime setting with GitHub config
    config_setting = RuntimeSettings(
        key="interventions.issue_provider", value=github_config
    )

    mock_db.query.return_value.filter.return_value.first.return_value = config_setting

    # Create watcher
    watcher = InvariantWatcher(mock_db)

    # Create a test incident
    incident = Incident(
        id=123,
        kind="invariant",
        key="test_inv_1",
        severity="sev2",
        status="open",
        summary="Test invariant failure",
        details={
            "agent": "gpt-4",
            "invariant_name": "test_check",
            "failure_message": "Test failure",
        },
    )

    # Mock the adapter and response
    with patch("app.intervene.watcher.IssueAdapterFactory") as mock_factory:
        mock_adapter = Mock()
        mock_response = Mock()
        mock_response.success = True
        mock_response.issue_url = "https://github.com/testorg/testrepo/issues/42"
        mock_adapter.create_issue.return_value = mock_response
        mock_factory.create.return_value = mock_adapter

        # Mock render_incident_issue
        with patch("app.intervene.watcher.render_incident_issue") as mock_render:
            mock_render.return_value = ("Test Issue", "Issue body")

            # Call _create_external_issue
            issue_url = watcher._create_external_issue(incident)

            # Verify issue was created
            assert issue_url == "https://github.com/testorg/testrepo/issues/42"

            # Verify adapter was called correctly
            mock_factory.create.assert_called_once_with(
                "github", github_config["config"]
            )
            mock_adapter.create_issue.assert_called_once()

            # Verify template was rendered
            mock_render.assert_called_once_with(incident)


def test_watcher_skips_external_issue_when_not_configured(mock_db):
    """Test that watcher gracefully skips issue creation when not configured."""

    # Setup: No config setting
    mock_db.query.return_value.filter.return_value.first.return_value = None

    watcher = InvariantWatcher(mock_db)

    incident = Incident(
        id=123,
        kind="invariant",
        key="test_inv_1",
        severity="sev2",
        status="open",
        summary="Test failure",
        details={},
    )

    # Should return None without error
    issue_url = watcher._create_external_issue(incident)
    assert issue_url is None


def test_watcher_handles_adapter_failure_gracefully(mock_db, github_config):
    """Test that watcher handles adapter failures without crashing."""

    config_setting = RuntimeSettings(
        key="interventions.issue_provider", value=github_config
    )
    mock_db.query.return_value.filter.return_value.first.return_value = config_setting

    watcher = InvariantWatcher(mock_db)

    incident = Incident(
        id=123,
        kind="invariant",
        key="test_inv_1",
        severity="sev2",
        status="open",
        summary="Test failure",
        details={},
    )

    # Mock adapter that fails
    with patch("app.intervene.watcher.IssueAdapterFactory") as mock_factory:
        mock_adapter = Mock()
        mock_response = Mock()
        mock_response.success = False
        mock_response.error = "API rate limit exceeded"
        mock_adapter.create_issue.return_value = mock_response
        mock_factory.create.return_value = mock_adapter

        with patch("app.intervene.watcher.render_incident_issue") as mock_render:
            mock_render.return_value = ("Test", "Body")

            # Should return None, not raise
            issue_url = watcher._create_external_issue(incident)
            assert issue_url is None


def test_watcher_handles_adapter_exception(mock_db, github_config):
    """Test that watcher handles adapter exceptions without crashing."""

    config_setting = RuntimeSettings(
        key="interventions.issue_provider", value=github_config
    )
    mock_db.query.return_value.filter.return_value.first.return_value = config_setting

    watcher = InvariantWatcher(mock_db)

    incident = Incident(
        id=123,
        kind="invariant",
        key="test_inv_1",
        severity="sev2",
        status="open",
        summary="Test failure",
        details={},
    )

    # Mock adapter that raises exception
    with patch("app.intervene.watcher.IssueAdapterFactory") as mock_factory:
        mock_factory.create.side_effect = Exception("Network error")

        # Should return None, not raise
        issue_url = watcher._create_external_issue(incident)
        assert issue_url is None


@patch("app.intervene.watcher.render_incident_issue")
@patch("app.intervene.watcher.IssueAdapterFactory")
def test_watcher_passes_correct_labels_to_adapter(
    mock_factory, mock_render, mock_db, github_config
):
    """Test that watcher passes correct labels and priority to adapter."""

    config_setting = RuntimeSettings(
        key="interventions.issue_provider", value=github_config
    )
    mock_db.query.return_value.filter.return_value.first.return_value = config_setting

    watcher = InvariantWatcher(mock_db)

    incident = Incident(
        id=123,
        kind="budget",
        key="test_budget",
        severity="sev1",
        status="open",
        summary="Critical budget overrun",
        details={},
    )

    # Mock successful response
    mock_adapter = Mock()
    mock_response = Mock()
    mock_response.success = True
    mock_response.issue_url = "https://github.com/test/test/issues/1"
    mock_adapter.create_issue.return_value = mock_response
    mock_factory.create.return_value = mock_adapter

    mock_render.return_value = ("Budget Alert", "Budget exceeded")

    # Create external issue
    watcher._create_external_issue(incident)

    # Verify labels include severity and kind
    call_args = mock_adapter.create_issue.call_args
    request = call_args[0][0]

    assert "sev1" in request.labels
    assert "budget" in request.labels
    assert request.priority == "sev1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
