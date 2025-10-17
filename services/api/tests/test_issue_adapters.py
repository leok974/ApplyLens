"""
Tests for issue adapters - Phase 5.4 PR2

Tests GitHub, GitLab, and Jira adapters with mocked HTTP calls.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.intervene.adapters.base import (
    IssueAdapter,
    IssueCreateRequest,
    IssueAdapterFactory,
    IssueAdapterError
)
from app.intervene.adapters.github import GitHubAdapter
from app.intervene.adapters.gitlab import GitLabAdapter
from app.intervene.adapters.jira import JiraAdapter


def test_issue_create_request():
    """Test IssueCreateRequest dataclass."""
    request = IssueCreateRequest(
        title="Test Issue",
        body="Issue description",
        labels=["bug", "urgent"],
        priority="P1",
    )
    
    assert request.title == "Test Issue"
    assert len(request.labels) == 2
    assert request.attachments == []


def test_adapter_factory_registration():
    """Test adapter factory registration."""
    providers = IssueAdapterFactory.list_providers()
    
    assert "github" in providers
    assert "gitlab" in providers
    assert "jira" in providers


def test_adapter_factory_create_github():
    """Test creating GitHub adapter via factory."""
    config = {
        "token": "ghp_test123",
        "owner": "testorg",
        "repo": "testrepo",
    }
    
    adapter = IssueAdapterFactory.create("github", config)
    
    assert isinstance(adapter, GitHubAdapter)
    assert adapter.owner == "testorg"
    assert adapter.repo == "testrepo"


def test_adapter_factory_unknown_provider():
    """Test factory with unknown provider."""
    with pytest.raises(ValueError, match="Unknown issue provider"):
        IssueAdapterFactory.create("unknown", {})


def test_github_adapter_validation():
    """Test GitHub adapter config validation."""
    # Valid config
    config = {
        "token": "ghp_test123",
        "owner": "testorg",
        "repo": "testrepo",
    }
    adapter = GitHubAdapter(config)
    assert adapter.validate_config() is True
    
    # Missing required keys
    with pytest.raises(IssueAdapterError):
        GitHubAdapter({"token": "test"})


@patch('requests.post')
def test_github_create_issue_success(mock_post):
    """Test successful GitHub issue creation."""
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "number": 123,
        "html_url": "https://github.com/testorg/testrepo/issues/123"
    }
    mock_post.return_value = mock_response
    
    # Create adapter
    config = {
        "token": "ghp_test123",
        "owner": "testorg",
        "repo": "testrepo",
    }
    adapter = GitHubAdapter(config)
    
    # Create issue
    request = IssueCreateRequest(
        title="Test Bug",
        body="Bug description",
        labels=["bug"],
        priority="P1",
    )
    
    response = adapter.create_issue(request)
    
    assert response.success is True
    assert response.issue_id == "123"
    assert "github.com" in response.issue_url
    
    # Verify API call
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "testorg/testrepo" in call_args[0][0]
    assert call_args[1]["json"]["title"] == "Test Bug"


@patch('requests.post')
def test_github_create_issue_failure(mock_post):
    """Test failed GitHub issue creation."""
    # Mock failed response
    mock_post.side_effect = Exception("API error")
    
    config = {
        "token": "ghp_test123",
        "owner": "testorg",
        "repo": "testrepo",
    }
    adapter = GitHubAdapter(config)
    
    request = IssueCreateRequest(
        title="Test Bug",
        body="Bug description",
        labels=["bug"],
    )
    
    response = adapter.create_issue(request)
    
    assert response.success is False
    assert response.error is not None


@patch('requests.post')
def test_github_update_issue(mock_post):
    """Test GitHub issue update."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
    config = {
        "token": "ghp_test123",
        "owner": "testorg",
        "repo": "testrepo",
    }
    adapter = GitHubAdapter(config)
    
    # Add comment
    result = adapter.update_issue("123", comment="Test comment")
    assert result is True
    
    # Verify comment endpoint called
    assert "comments" in mock_post.call_args[0][0]


@patch('requests.get')
def test_github_test_connection(mock_get):
    """Test GitHub connection test."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    config = {
        "token": "ghp_test123",
        "owner": "testorg",
        "repo": "testrepo",
    }
    adapter = GitHubAdapter(config)
    
    assert adapter.test_connection() is True


def test_gitlab_adapter_validation():
    """Test GitLab adapter config validation."""
    config = {
        "token": "glpat_test123",
        "project_id": "group/project",
    }
    adapter = GitLabAdapter(config)
    assert adapter.validate_config() is True
    
    # Missing required keys
    with pytest.raises(IssueAdapterError):
        GitLabAdapter({"token": "test"})


@patch('requests.post')
def test_gitlab_create_issue(mock_post):
    """Test GitLab issue creation."""
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "iid": 456,
        "web_url": "https://gitlab.com/group/project/-/issues/456"
    }
    mock_post.return_value = mock_response
    
    config = {
        "token": "glpat_test123",
        "project_id": "group/project",
    }
    adapter = GitLabAdapter(config)
    
    request = IssueCreateRequest(
        title="Test Issue",
        body="Issue body",
        labels=["bug"],
    )
    
    response = adapter.create_issue(request)
    
    assert response.success is True
    assert response.issue_id == "456"
    assert "gitlab.com" in response.issue_url


def test_jira_adapter_validation():
    """Test Jira adapter config validation."""
    config = {
        "base_url": "https://company.atlassian.net",
        "email": "user@company.com",
        "api_token": "token123",
        "project_key": "PROD",
    }
    adapter = JiraAdapter(config)
    assert adapter.validate_config() is True
    
    # Missing required keys
    with pytest.raises(IssueAdapterError):
        JiraAdapter({"base_url": "https://test.atlassian.net"})


@patch('requests.post')
def test_jira_create_issue(mock_post):
    """Test Jira issue creation."""
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "key": "PROD-789",
    }
    mock_post.return_value = mock_response
    
    config = {
        "base_url": "https://company.atlassian.net",
        "email": "user@company.com",
        "api_token": "token123",
        "project_key": "PROD",
    }
    adapter = JiraAdapter(config)
    
    request = IssueCreateRequest(
        title="Production Issue",
        body="Issue description",
        labels=["incident"],
        priority="sev1",
    )
    
    response = adapter.create_issue(request)
    
    assert response.success is True
    assert response.issue_id == "PROD-789"
    assert "PROD-789" in response.issue_url
    
    # Verify priority mapping
    call_json = mock_post.call_args[1]["json"]
    assert call_json["fields"]["priority"]["name"] == "Highest"  # sev1 → Highest


@patch('requests.post')
def test_jira_create_issue_with_description(mock_post):
    """Test Jira issue with proper description format."""
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"key": "PROD-123"}
    mock_post.return_value = mock_response
    
    config = {
        "base_url": "https://company.atlassian.net",
        "email": "user@company.com",
        "api_token": "token123",
        "project_key": "PROD",
    }
    adapter = JiraAdapter(config)
    
    request = IssueCreateRequest(
        title="Test",
        body="Multi-line\ndescription\ntext",
        labels=[],
    )
    
    adapter.create_issue(request)
    
    # Verify Atlassian Document Format structure
    call_json = mock_post.call_args[1]["json"]
    description = call_json["fields"]["description"]
    
    assert description["type"] == "doc"
    assert description["version"] == 1
    assert len(description["content"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
