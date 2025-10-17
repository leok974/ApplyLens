"""
GitLab issue adapter for Phase 5.4 PR2.

Creates issues in GitLab projects using GitLab REST API.
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


class GitLabAdapter(IssueAdapter):
    """
    Adapter for creating issues in GitLab.
    
    Required config:
        - token: GitLab personal access token
        - project_id: Project ID or path (e.g., "group/project")
    
    Optional config:
        - base_url: GitLab API base URL (default: https://gitlab.com)
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://gitlab.com")
        self.token = config.get("token")
        self.project_id = config.get("project_id")
        
        if not self.validate_config():
            raise IssueAdapterError("Missing required GitLab configuration")
    
    def get_required_config_keys(self) -> List[str]:
        return ["token", "project_id"]
    
    def create_issue(self, request: IssueCreateRequest) -> IssueCreateResponse:
        """Create GitLab issue via REST API."""
        # URL-encode project ID
        import urllib.parse
        project_path = urllib.parse.quote(str(self.project_id), safe='')
        url = f"{self.base_url}/api/v4/projects/{project_path}/issues"
        
        headers = {
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json",
        }
        
        # Build payload
        payload = {
            "title": request.title,
            "description": request.body,
            "labels": ",".join(request.labels) if request.labels else "",
        }
        
        if request.assignee:
            # Would need to resolve username to user ID
            payload["assignee_ids"] = []  # Placeholder
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            issue_iid = data.get("iid")  # Internal ID
            issue_url = data.get("web_url")
            
            logger.info(f"Created GitLab issue !{issue_iid}: {issue_url}")
            
            return IssueCreateResponse(
                success=True,
                issue_id=str(issue_iid),
                issue_url=issue_url,
            )
            
        except requests.RequestException as e:
            logger.error(f"Failed to create GitLab issue: {e}")
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
        """Update GitLab issue."""
        import urllib.parse
        project_path = urllib.parse.quote(str(self.project_id), safe='')
        
        try:
            # Add comment (note)
            if comment:
                note_url = (
                    f"{self.base_url}/api/v4/projects/{project_path}"
                    f"/issues/{issue_id}/notes"
                )
                headers = {"PRIVATE-TOKEN": self.token}
                requests.post(
                    note_url,
                    headers=headers,
                    json={"body": comment},
                    timeout=30
                ).raise_for_status()
            
            # Update labels or status
            if labels or status:
                issue_url = (
                    f"{self.base_url}/api/v4/projects/{project_path}"
                    f"/issues/{issue_id}"
                )
                headers = {"PRIVATE-TOKEN": self.token}
                payload = {}
                if labels:
                    payload["labels"] = ",".join(labels)
                if status and status.lower() in ["closed", "resolved"]:
                    payload["state_event"] = "close"
                
                requests.put(
                    issue_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                ).raise_for_status()
            
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to update GitLab issue !{issue_id}: {e}")
            return False
    
    def close_issue(self, issue_id: str, comment: Optional[str] = None) -> bool:
        """Close GitLab issue."""
        if comment:
            self.update_issue(issue_id, comment=comment)
        
        return self.update_issue(issue_id, status="closed")
    
    def test_connection(self) -> bool:
        """Test GitLab API connectivity."""
        try:
            import urllib.parse
            project_path = urllib.parse.quote(str(self.project_id), safe='')
            url = f"{self.base_url}/api/v4/projects/{project_path}"
            headers = {"PRIVATE-TOKEN": self.token}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"GitLab connection test failed: {e}")
            return False


# Register with factory
IssueAdapterFactory.register("gitlab", GitLabAdapter)
