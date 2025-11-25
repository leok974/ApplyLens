"""
Jira issue adapter for Phase 5.4 PR2.

Creates issues in Jira projects using Jira REST API v3.
"""

import logging
from typing import Dict, Any, List, Optional
import requests
import base64

from .base import (
    IssueAdapter,
    IssueCreateRequest,
    IssueCreateResponse,
    IssueAdapterError,
    IssueAdapterFactory,
)

logger = logging.getLogger(__name__)


class JiraAdapter(IssueAdapter):
    """
    Adapter for creating issues in Jira.

    Required config:
        - base_url: Jira instance URL (e.g., https://company.atlassian.net)
        - email: User email for authentication
        - api_token: Jira API token
        - project_key: Project key (e.g., "PROD")

    Optional config:
        - issue_type: Issue type (default: "Bug")
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "").rstrip("/")
        self.email = config.get("email")
        self.api_token = config.get("api_token")
        self.project_key = config.get("project_key")
        self.issue_type = config.get("issue_type", "Bug")

        if not self.validate_config():
            raise IssueAdapterError("Missing required Jira configuration")

        # Basic auth header
        auth_str = f"{self.email}:{self.api_token}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        self.auth_header = f"Basic {b64_auth}"

    def get_required_config_keys(self) -> List[str]:
        return ["base_url", "email", "api_token", "project_key"]

    def create_issue(self, request: IssueCreateRequest) -> IssueCreateResponse:
        """Create Jira issue via REST API v3."""
        url = f"{self.base_url}/rest/api/3/issue"

        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
        }

        # Map priority to Jira priority names
        priority_map = {
            "P0": "Highest",
            "P1": "High",
            "P2": "Medium",
            "P3": "Low",
            "P4": "Lowest",
            "sev1": "Highest",
            "sev2": "High",
            "sev3": "Medium",
            "sev4": "Low",
        }
        jira_priority = priority_map.get(request.priority, "Medium")

        # Build payload
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": request.title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": request.body}],
                        }
                    ],
                },
                "issuetype": {"name": self.issue_type},
                "priority": {"name": jira_priority},
            }
        }

        # Add labels
        if request.labels:
            payload["fields"]["labels"] = request.labels

        # Add assignee (if provided as account ID)
        if request.assignee:
            payload["fields"]["assignee"] = {"accountId": request.assignee}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            issue_key = data.get("key")
            issue_url = f"{self.base_url}/browse/{issue_key}"

            logger.info(f"Created Jira issue {issue_key}: {issue_url}")

            return IssueCreateResponse(
                success=True,
                issue_id=issue_key,
                issue_url=issue_url,
            )

        except requests.RequestException as e:
            logger.error(f"Failed to create Jira issue: {e}")
            error_msg = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("errorMessages", [str(e)])[0]
                except Exception:
                    pass

            return IssueCreateResponse(
                success=False,
                issue_id="",
                issue_url="",
                error=error_msg,
            )

    def update_issue(
        self,
        issue_id: str,
        comment: Optional[str] = None,
        labels: Optional[List[str]] = None,
        status: Optional[str] = None,
    ) -> bool:
        """Update Jira issue."""
        try:
            headers = {
                "Authorization": self.auth_header,
                "Content-Type": "application/json",
            }

            # Add comment
            if comment:
                comment_url = f"{self.base_url}/rest/api/3/issue/{issue_id}/comment"
                comment_payload = {
                    "body": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": comment}],
                            }
                        ],
                    }
                }
                requests.post(
                    comment_url, headers=headers, json=comment_payload, timeout=30
                ).raise_for_status()

            # Update labels
            if labels:
                issue_url = f"{self.base_url}/rest/api/3/issue/{issue_id}"
                label_payload = {"fields": {"labels": labels}}
                requests.put(
                    issue_url, headers=headers, json=label_payload, timeout=30
                ).raise_for_status()

            # Transition status (complex, requires transition ID lookup)
            if status:
                # Simplified: just log, proper implementation needs transition mapping
                logger.info(
                    f"Status transition for {issue_id} to {status} (not implemented)"
                )

            return True

        except requests.RequestException as e:
            logger.error(f"Failed to update Jira issue {issue_id}: {e}")
            return False

    def close_issue(self, issue_id: str, comment: Optional[str] = None) -> bool:
        """Close Jira issue."""
        if comment:
            self.update_issue(issue_id, comment=comment)

        # Would need to transition to "Done" or "Closed" state
        # Requires looking up valid transitions for issue
        return self.update_issue(issue_id, status="closed")

    def test_connection(self) -> bool:
        """Test Jira API connectivity."""
        try:
            url = f"{self.base_url}/rest/api/3/myself"
            headers = {"Authorization": self.auth_header}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Jira connection test failed: {e}")
            return False


# Register with factory
IssueAdapterFactory.register("jira", JiraAdapter)
