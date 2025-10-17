"""
GitHub issue adapter for Phase 5.4 PR2.

Creates issues in GitHub repositories using GitHub REST API.
"""
import logging
from typing import Dict, Any, List, Optional
import requests

from .base import (
    IssueAdapter,
    IssueCreateRequest,
    IssueCreateResponse,
    IssueAdapterError,
    IssueAdapterFactory
)

logger = logging.getLogger(__name__)


class GitHubAdapter(IssueAdapter):
    """
    Adapter for creating issues in GitHub.
    
    Required config:
        - token: GitHub personal access token or App token
        - owner: Repository owner (username or org)
        - repo: Repository name
    
    Optional config:
        - base_url: GitHub API base URL (default: https://api.github.com)
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://api.github.com")
        self.token = config.get("token")
        self.owner = config.get("owner")
        self.repo = config.get("repo")
        
        if not self.validate_config():
            raise IssueAdapterError("Missing required GitHub configuration")
    
    def get_required_config_keys(self) -> List[str]:
        return ["token", "owner", "repo"]
    
    def create_issue(self, request: IssueCreateRequest) -> IssueCreateResponse:
        """Create GitHub issue via REST API."""
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues"
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
        
        # Map priority to labels
        labels = list(request.labels)
        if request.priority:
            labels.append(f"priority:{request.priority.lower()}")
        
        # Build payload
        payload = {
            "title": request.title,
            "body": request.body,
            "labels": labels,
        }
        
        if request.assignee:
            payload["assignees"] = [request.assignee]
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            issue_number = data.get("number")
            issue_url = data.get("html_url")
            
            logger.info(f"Created GitHub issue #{issue_number}: {issue_url}")
            
            return IssueCreateResponse(
                success=True,
                issue_id=str(issue_number),
                issue_url=issue_url,
            )
            
        except requests.RequestException as e:
            logger.error(f"Failed to create GitHub issue: {e}")
            return IssueCreateResponse(
                success=False,
                issue_id="",
                issue_url="",
                error=str(e),
            )
    
    def update_issue(
        self,
        issue_id: str,
        comment: Optional[str] = None,
        labels: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> bool:
        """Update GitHub issue."""
        try:
            # Add comment
            if comment:
                comment_url = (
                    f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{issue_id}/comments"
                )
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                }
                requests.post(
                    comment_url,
                    headers=headers,
                    json={"body": comment},
                    timeout=30
                ).raise_for_status()
            
            # Update labels or status
            if labels or status:
                issue_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{issue_id}"
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                }
                payload = {}
                if labels:
                    payload["labels"] = labels
                if status:
                    # Map generic status to GitHub state
                    if status.lower() in ["closed", "resolved"]:
                        payload["state"] = "closed"
                
                requests.patch(
                    issue_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                ).raise_for_status()
            
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to update GitHub issue #{issue_id}: {e}")
            return False
    
    def close_issue(self, issue_id: str, comment: Optional[str] = None) -> bool:
        """Close GitHub issue."""
        if comment:
            self.update_issue(issue_id, comment=comment)
        
        return self.update_issue(issue_id, status="closed")
    
    def test_connection(self) -> bool:
        """Test GitHub API connectivity."""
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo}"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"GitHub connection test failed: {e}")
            return False


# Register with factory
IssueAdapterFactory.register("github", GitHubAdapter)
