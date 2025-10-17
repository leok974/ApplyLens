"""
Mock Issue Tracker APIs - Phase 5.4 PR6

Mock responses for GitHub, GitLab, and Jira APIs.
Used in tests to avoid real API calls.
"""
from typing import Dict, Any, Optional, List
from unittest.mock import Mock
import json


class MockResponse:
    """Mock HTTP response."""
    
    def __init__(self, status_code: int, json_data: Optional[Dict] = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.ok = 200 <= status_code < 300
    
    def json(self):
        return self._json_data
    
    def raise_for_status(self):
        if not self.ok:
            raise Exception(f"HTTP {self.status_code}: {self.text}")


class MockGitHubAPI:
    """
    Mock GitHub REST API v3.
    
    Returns realistic responses for issue operations.
    """
    
    def __init__(self):
        self.issues_created: List[Dict[str, Any]] = []
        self.comments_added: List[Dict[str, Any]] = []
        self.issues_closed: List[int] = []
        self.next_issue_number = 1
    
    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> MockResponse:
        """Mock POST /repos/{owner}/{repo}/issues."""
        issue = {
            "number": self.next_issue_number,
            "title": title,
            "body": body,
            "labels": [{"name": label} for label in (labels or [])],
            "assignees": [{"login": user} for user in (assignees or [])],
            "state": "open",
            "html_url": f"https://github.com/{owner}/{repo}/issues/{self.next_issue_number}",
            "created_at": "2025-10-17T12:00:00Z",
            "updated_at": "2025-10-17T12:00:00Z",
        }
        
        self.issues_created.append(issue)
        self.next_issue_number += 1
        
        return MockResponse(201, issue)
    
    def add_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> MockResponse:
        """Mock POST /repos/{owner}/{repo}/issues/{issue_number}/comments."""
        comment = {
            "id": len(self.comments_added) + 1,
            "body": body,
            "issue_url": f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}",
            "html_url": f"https://github.com/{owner}/{repo}/issues/{issue_number}#issuecomment-{len(self.comments_added) + 1}",
            "created_at": "2025-10-17T12:05:00Z",
        }
        
        self.comments_added.append(comment)
        
        return MockResponse(201, comment)
    
    def close_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
    ) -> MockResponse:
        """Mock PATCH /repos/{owner}/{repo}/issues/{issue_number}."""
        self.issues_closed.append(issue_number)
        
        return MockResponse(200, {
            "number": issue_number,
            "state": "closed",
            "closed_at": "2025-10-17T12:10:00Z",
        })
    
    def get_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
    ) -> MockResponse:
        """Mock GET /repos/{owner}/{repo}/issues/{issue_number}."""
        # Find in created issues
        for issue in self.issues_created:
            if issue["number"] == issue_number:
                return MockResponse(200, issue)
        
        # Not found
        return MockResponse(404, {"message": "Not Found"})
    
    def reset(self):
        """Reset all tracking."""
        self.issues_created = []
        self.comments_added = []
        self.issues_closed = []
        self.next_issue_number = 1


class MockGitLabAPI:
    """
    Mock GitLab REST API v4.
    
    Returns realistic responses for issue operations.
    """
    
    def __init__(self):
        self.issues_created: List[Dict[str, Any]] = []
        self.notes_added: List[Dict[str, Any]] = []
        self.issues_closed: List[int] = []
        self.next_issue_iid = 1
    
    def create_issue(
        self,
        project_id: str,
        title: str,
        description: str,
        labels: Optional[List[str]] = None,
        assignee_ids: Optional[List[int]] = None,
    ) -> MockResponse:
        """Mock POST /projects/{id}/issues."""
        issue = {
            "iid": self.next_issue_iid,
            "id": self.next_issue_iid * 100,
            "title": title,
            "description": description,
            "labels": labels or [],
            "assignees": [{"id": aid, "username": f"user{aid}"} for aid in (assignee_ids or [])],
            "state": "opened",
            "web_url": f"https://gitlab.com/{project_id}/issues/{self.next_issue_iid}",
            "created_at": "2025-10-17T12:00:00Z",
            "updated_at": "2025-10-17T12:00:00Z",
        }
        
        self.issues_created.append(issue)
        self.next_issue_iid += 1
        
        return MockResponse(201, issue)
    
    def add_note(
        self,
        project_id: str,
        issue_iid: int,
        body: str,
    ) -> MockResponse:
        """Mock POST /projects/{id}/issues/{iid}/notes."""
        note = {
            "id": len(self.notes_added) + 1,
            "body": body,
            "noteable_type": "Issue",
            "noteable_iid": issue_iid,
            "created_at": "2025-10-17T12:05:00Z",
        }
        
        self.notes_added.append(note)
        
        return MockResponse(201, note)
    
    def close_issue(
        self,
        project_id: str,
        issue_iid: int,
    ) -> MockResponse:
        """Mock PUT /projects/{id}/issues/{iid}."""
        self.issues_closed.append(issue_iid)
        
        return MockResponse(200, {
            "iid": issue_iid,
            "state": "closed",
            "closed_at": "2025-10-17T12:10:00Z",
        })
    
    def get_issue(
        self,
        project_id: str,
        issue_iid: int,
    ) -> MockResponse:
        """Mock GET /projects/{id}/issues/{iid}."""
        for issue in self.issues_created:
            if issue["iid"] == issue_iid:
                return MockResponse(200, issue)
        
        return MockResponse(404, {"message": "404 Issue Not Found"})
    
    def reset(self):
        """Reset all tracking."""
        self.issues_created = []
        self.notes_added = []
        self.issues_closed = []
        self.next_issue_iid = 1


class MockJiraAPI:
    """
    Mock Jira REST API v3.
    
    Returns realistic responses for issue operations.
    """
    
    def __init__(self):
        self.issues_created: List[Dict[str, Any]] = []
        self.comments_added: List[Dict[str, Any]] = []
        self.issues_transitioned: List[Dict[str, Any]] = []
        self.next_issue_key = 1
    
    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: Dict[str, Any],  # ADF format
        issue_type: str = "Bug",
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None,
    ) -> MockResponse:
        """Mock POST /rest/api/3/issue."""
        issue_key = f"{project_key}-{self.next_issue_key}"
        
        issue = {
            "id": str(self.next_issue_key * 10000),
            "key": issue_key,
            "self": f"https://jira.example.com/rest/api/3/issue/{self.next_issue_key * 10000}",
            "fields": {
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
                "labels": labels or [],
                "assignee": {"accountId": assignee} if assignee else None,
                "status": {"name": "Open"},
                "created": "2025-10-17T12:00:00.000+0000",
                "updated": "2025-10-17T12:00:00.000+0000",
            },
        }
        
        self.issues_created.append(issue)
        self.next_issue_key += 1
        
        return MockResponse(201, {
            "id": issue["id"],
            "key": issue_key,
            "self": issue["self"],
        })
    
    def add_comment(
        self,
        issue_key: str,
        body: Dict[str, Any],  # ADF format
    ) -> MockResponse:
        """Mock POST /rest/api/3/issue/{issueIdOrKey}/comment."""
        comment = {
            "id": str(len(self.comments_added) + 1),
            "body": body,
            "created": "2025-10-17T12:05:00.000+0000",
        }
        
        self.comments_added.append(comment)
        
        return MockResponse(201, comment)
    
    def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
    ) -> MockResponse:
        """Mock POST /rest/api/3/issue/{issueIdOrKey}/transitions."""
        self.issues_transitioned.append({
            "issue_key": issue_key,
            "transition_id": transition_id,
        })
        
        return MockResponse(204)
    
    def get_issue(
        self,
        issue_key: str,
    ) -> MockResponse:
        """Mock GET /rest/api/3/issue/{issueIdOrKey}."""
        for issue in self.issues_created:
            if issue["key"] == issue_key:
                return MockResponse(200, issue)
        
        return MockResponse(404, {"errorMessages": ["Issue does not exist"]})
    
    def reset(self):
        """Reset all tracking."""
        self.issues_created = []
        self.comments_added = []
        self.issues_transitioned = []
        self.next_issue_key = 1


# Global mock instances for reuse
mock_github = MockGitHubAPI()
mock_gitlab = MockGitLabAPI()
mock_jira = MockJiraAPI()


def reset_all_mocks():
    """Reset all mock APIs to initial state."""
    mock_github.reset()
    mock_gitlab.reset()
    mock_jira.reset()
