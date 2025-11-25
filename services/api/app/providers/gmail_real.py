"""Real Gmail provider implementation.

Integrates with Gmail API using OAuth2 credentials.
Phase 2: Uses existing oauth_google module infrastructure.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..schemas.tools import GmailSearchResponse


class GmailProvider:
    """Real Gmail API provider.

    Uses Gmail API v1 with OAuth2 authentication.
    Requires GMAIL_OAUTH_SECRETS_PATH and GMAIL_OAUTH_TOKEN_PATH.
    """

    def __init__(self, secrets_path: str | None = None, token_path: str | None = None):
        """Initialize Gmail provider.

        Args:
            secrets_path: Path to OAuth2 client secrets JSON
            token_path: Path to OAuth2 token JSON
        """
        self.secrets_path = secrets_path or os.getenv("GMAIL_OAUTH_SECRETS_PATH")
        self.token_path = token_path or os.getenv("GMAIL_OAUTH_TOKEN_PATH")
        self._service = None

    def _get_service(self):
        """Lazy-load Gmail API service.

        Returns:
            Gmail API service instance
        """
        if self._service is None:
            # Phase 2: Integrate with existing oauth_google module
            # For now, raise NotImplementedError to be implemented
            try:
                from googleapiclient.discovery import build
                from google.oauth2.credentials import Credentials

                # Load credentials (simplified - needs proper OAuth flow)
                creds = Credentials.from_authorized_user_file(self.token_path)
                self._service = build("gmail", "v1", credentials=creds)
            except Exception as e:
                raise NotImplementedError(
                    f"Gmail API integration pending: {e}. "
                    "Set APPLYLENS_PROVIDERS=mock for testing."
                )
        return self._service

    def search_recent(self, days: int = 7) -> "GmailSearchResponse":
        """Search for recent emails.

        Args:
            days: Number of days to look back

        Returns:
            Search response with matching messages
        """
        from ..schemas.tools import GmailMessage, GmailSearchResponse
        from datetime import datetime, timedelta

        service = self._get_service()

        # Build query for recent messages
        after_date = datetime.now() - timedelta(days=days)
        query = f"after:{after_date.strftime('%Y/%m/%d')}"

        # Execute search
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=100)
            .execute()
        )

        messages = []
        for msg in results.get("messages", []):
            # Get full message details
            full_msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )

            headers = {
                h["name"]: h["value"]
                for h in full_msg.get("payload", {}).get("headers", [])
            }

            messages.append(
                GmailMessage(
                    id=msg["id"],
                    thread_id=full_msg.get("threadId", ""),
                    subject=headers.get("Subject", ""),
                    from_addr=headers.get("From", ""),
                    received_at=headers.get("Date", ""),
                )
            )

        return GmailSearchResponse(messages=messages)
